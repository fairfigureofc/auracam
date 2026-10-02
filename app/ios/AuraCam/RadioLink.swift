import Foundation
import CoreBluetooth
import CryptoKit
import Combine


final class RadioLink: NSObject, ObservableObject, CBCentralManagerDelegate, CBPeripheralDelegate {
    static let service = CBUUID(string: "9d7a0001-64d8-4ef1-9b9e-7127ba10ca00")
    let commandID = CBUUID(string: "9d7a0002-64d8-4ef1-9b9e-7127ba10ca00")
    let responseID = CBUUID(string: "9d7a0003-64d8-4ef1-9b9e-7127ba10ca00")
    @Published var library: [CaptureEntry] = []
    @Published var libraryLoaded = false
    @Published var libraryBusy = false
    @Published var nameSaveRevision = 0
    private var expectedName: (id: String, name: String)?
    @Published var awaitingCapture = false
    private var previousCaptureID: String?
    @Published var status = "Not connected"
    @Published var ready = false
    @Published var working = false
    @Published var commandPending = false
    @Published var commandStatus: String?
    private var queuedAction: (() -> Void)?
    @Published var state = RadioState()
    @Published var progress: Double = 0
    @Published var downloading: String?
    @Published var error: String?
    @Published var images: [LocalImage] = []
    @Published var devices: [CBPeripheral] = []
    private var pollingPaused = false
    private var rediscoveredAfterInvalidHandle = false
    private var central: CBCentralManager!
    private var peripheral: CBPeripheral?
    private var command: CBCharacteristic?
    private var response: CBCharacteristic?
    private var writes: [Data] = []
    private var buffer = Data()
    private var total = 0
    private var checksum = ""
    private var receivingMeta = true
    private var completion: ((Data) -> Void)?
    private var deadline: Timer?
    private var poller: Timer?
    @Published var countdown: Int?
    private let directory: URL
    override init() {
        directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("Captures", isDirectory: true)
        super.init()
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        loadImages()
        central = CBCentralManager(delegate: self, queue: .main)
        poller = Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in self?.refresh() }
    }
    func loadImages() {
        images = ((try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)) ?? []).filter { $0.pathExtension == "png" }.sorted { $0.lastPathComponent > $1.lastPathComponent }.map { LocalImage(url: $0) }
    }
    func scan() {
        guard central.state == .poweredOn else { status = "Turn on Bluetooth in Settings"; return }
        devices = []; status = "Looking for AuraCam…"
        central.scanForPeripherals(withServices: [Self.service])
    }
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state == .poweredOn { scan() }
        else { ready = false; status = central.state == .unauthorized ? "Allow Bluetooth in Settings" : "Bluetooth unavailable" }
    }
    func centralManager(_ central: CBCentralManager, didDiscover p: CBPeripheral, advertisementData: [String: Any], rssi RSSI: NSNumber) {
        if !devices.contains(where: { $0.identifier == p.identifier }) { devices.append(p) }
    }
    func connect(_ p: CBPeripheral) {
        central.stopScan(); peripheral = p; p.delegate = self
        pollingPaused = false; rediscoveredAfterInvalidHandle = false
        ready = false; command = nil; response = nil; error = nil
        if p.state == .connected { status = "Checking instrument…"; p.discoverServices([Self.service]) }
        else { status = "Connecting…"; central.connect(p) }
    }
    func centralManager(_ central: CBCentralManager, didConnect p: CBPeripheral) { status = "Discovering controls…"; p.discoverServices([Self.service]) }
    func centralManager(_ central: CBCentralManager, didFailToConnect p: CBPeripheral, error: Error?) { fail(error?.localizedDescription ?? "Connection failed"); status = "Tap to reconnect" }
    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral p: CBPeripheral, error: Error?) {
        ready = false; command = nil; response = nil; fail("Disconnected. Reconnect, then retry your download."); status = "Disconnected"; scan()
    }
    func peripheral(_ p: CBPeripheral, didDiscoverServices error: Error?) {
        if let error { fail(error.localizedDescription); return }
        for service in p.services ?? [] { p.discoverCharacteristics([commandID,responseID], for: service) }
    }
    func peripheral(_ p: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        if let error { fail(error.localizedDescription); return }
        for c in service.characteristics ?? [] { if c.uuid == commandID { command = c }; if c.uuid == responseID { response = c } }
        ready = command != nil && response != nil; status = ready ? "Checking encrypted connection…" : "Controls not found"; refresh()
    }
    func peripheral(_ p: CBPeripheral, didModifyServices invalidatedServices: [CBService]) {
        guard invalidatedServices.contains(where: { $0.uuid == Self.service }) else { return }
        fail("Instrument services restarted. Checking the connection; the previous command will not be replayed.")
        ready = false; command = nil; response = nil; pollingPaused = false
        status = "Refreshing instrument services…"
        p.discoverServices([Self.service])
    }
    private func transportFailed(_ failure: Error, peripheral p: CBPeripheral) {
        let error = failure as NSError
        fail(failure.localizedDescription)
        if error.domain == CBATTErrorDomain {
            pollingPaused = true; ready = false
            if error.code == CBATTError.Code.invalidHandle.rawValue && !rediscoveredAfterInvalidHandle {
                rediscoveredAfterInvalidHandle = true
                command = nil; response = nil; pollingPaused = false
                status = "Refreshing instrument services…"
                p.discoverServices([Self.service])
            } else if error.code == CBATTError.Code.insufficientEncryption.rawValue || error.code == CBATTError.Code.insufficientAuthentication.rawValue {
                status = "Pairing incomplete — retries paused"
                self.error = "Bluetooth encryption was not established. Automatic requests are paused. The Pi pairing log is needed; capture was not retried."
            } else { status = "Bluetooth request failed — tap Connect to retry" }
        }
    }
    private func fail(_ message: String) {
        deadline?.invalidate(); libraryBusy = false; expectedName = nil; awaitingCapture = false; queuedAction = nil; commandPending = false; commandStatus = nil; working = false; error = message; downloading = nil; completion = nil; writes = []; buffer = Data()
    }
    private func armTimeout() {
        deadline?.invalidate()
        deadline = Timer.scheduledTimer(withTimeInterval: 20, repeats: false) { [weak self] _ in
            guard let self else { return }; self.fail("Bluetooth request timed out. Reconnect and retry.")
            if let p = self.peripheral { self.central.cancelPeripheralConnection(p) }
        }
    }
    private func send(_ object: [String: Any]) {
        guard let p = peripheral, let command, let raw = try? JSONSerialization.data(withJSONObject: object) else { fail("Bluetooth is not ready"); return }
        let data = raw + Data([10]); let size = p.maximumWriteValueLength(for: .withResponse)
        guard size > 0 else { fail("Invalid Bluetooth packet size"); return }
        writes = stride(from: 0, to: data.count, by: size).map { data.subdata(in: $0..<min($0+size,data.count)) }
        armTimeout(); p.writeValue(writes.removeFirst(), for: command, type: .withResponse)
    }
    func peripheral(_ p: CBPeripheral, didWriteValueFor c: CBCharacteristic, error: Error?) {
        if let error { transportFailed(error, peripheral: p); return }
        guard working, let command, let response else { return }
        if !writes.isEmpty { p.writeValue(writes.removeFirst(), for: command, type: .withResponse) }
        else { p.readValue(for: response) }
    }
    private func request(_ object: [String: Any], done: @escaping (Data) -> Void) {
        guard ready, !working else { return }
        working = true; completion = done; buffer = Data(); receivingMeta = true; progress = 0; send(object)
    }
    func peripheral(_ p: CBPeripheral, didUpdateValueFor c: CBCharacteristic, error: Error?) {
        if let error { transportFailed(error, peripheral: p); return }
        guard working, c.uuid == responseID, let data = c.value else { return }
        deadline?.invalidate()
        if receivingMeta {
            guard let meta = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else { fail("Invalid transfer header"); return }
            if let message = meta["error"] as? String { fail(message); return }
            guard let length = meta["length"] as? Int, length >= 0, length <= 16*1024*1024, let hash = meta["sha256"] as? String else { fail("Invalid image size"); return }
            total = length; checksum = hash; receivingMeta = false
        } else {
            guard !data.isEmpty, buffer.count + data.count <= total else { fail("Incomplete transfer. Tap download to retry."); return }
            buffer.append(data); progress = Double(buffer.count)/Double(max(total,1))
        }
        if buffer.count == total {
            let hash = SHA256.hash(data: buffer).map { String(format: "%02x",$0) }.joined()
            guard hash == checksum else { fail("Transfer verification failed. Retry download."); return }
            let value = buffer; let done = completion; completion = nil; working = false; done?(value)
            if !working, let next = queuedAction { queuedAction = nil; next() }
        } else { send(["op":"read", "offset":buffer.count]) }
    }
    func refresh() {
        guard !pollingPaused, downloading == nil, !commandPending else { return }
        request(["op":"state"]) { [weak self] data in
            guard let self else { return }
            do {
                self.state = try JSONDecoder().decode(RadioState.self, from: data)
                self.status = "Instrument connected"
                if self.awaitingCapture, self.state.capture_id != self.previousCaptureID, self.state.stage == "gallery" { self.awaitingCapture = false }
                if self.state.stage == "error" { self.awaitingCapture = false; self.expectedName = nil }
                if let expected = self.expectedName, !self.state.busy,
                   self.state.capture_id == expected.id, self.state.capture_name == expected.name,
                   self.state.message == "Capture name saved." {
                    self.expectedName = nil; self.nameSaveRevision += 1
                }

            }
            catch { self.error = "Could not read instrument state" }
        }
    }
    func prepare(_ operation: String) {
        guard ready, countdown == nil, !commandPending, !state.busy else { return }
        if operation == "capture" { awaitingCapture = true; previousCaptureID = state.capture_id }
        countdown = 3
        Task { @MainActor in
            for n in (1...3).reversed() {
                self.countdown = n
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard self.ready else { self.countdown = nil; return }
            }
            self.countdown = nil
            self.action(operation, extra: ["countdown_done":true])
        }
    }
    func action(_ action: String, extra: [String: Any] = [:]) {
        guard ready else { error = "Connect to the instrument first."; return }
        guard !commandPending else { return }
        guard downloading == nil else { error = "Wait for the image download to finish."; return }
        error = nil
        if action == "name", let id = extra["capture_id"] as? String {
            let typed = (extra["name"] as? String ?? "").split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
            expectedName = (id, typed.isEmpty ? (state.capture_name ?? "") : typed)
        }
        commandPending = true
        commandStatus = working ? "Finishing status check…" : "Sending command…"
        var body = extra; body["action"] = action
        let execute: () -> Void = { [weak self] in
            guard let self else { return }
            self.commandStatus = "Sending command…"
            self.request(["op":"action", "body":body]) { [weak self] _ in
                guard let self else { return }
                self.commandPending = false
                self.commandStatus = nil
                self.refresh()
            }
        }
        if working { queuedAction = execute } else { execute() }
    }
    func loadLibrary() {
        guard ready, !commandPending, downloading == nil else { return }
        libraryBusy = true
        if working {
            commandPending = true
            queuedAction = { [weak self] in self?.commandPending = false; self?.loadLibrary() }
            return
        }
        request(["op":"library"]) { [weak self] data in
            guard let self else { return }
            self.libraryBusy = false
            do { self.library = try JSONDecoder().decode([CaptureEntry].self,from:data); self.libraryLoaded = true }
            catch { self.error = "The Pi needs the capture-library update, or returned an invalid library." }
        }
    }
    func deleteCapture(_ entry: CaptureEntry) {
        guard ready, !commandPending, downloading == nil else { return }
        if working {
            commandPending = true
            queuedAction = { [weak self] in self?.commandPending = false; self?.deleteCapture(entry) }
            return
        }
        commandPending = true
        request(["op":"action","body":["action":"delete","id":entry.id]]) { [weak self] _ in
            guard let self else { return }
            self.commandPending = false; self.loadLibrary()
        }
    }
    func download(_ path: String, captureName: String? = nil) {
        guard ready, !commandPending, downloading == nil else { return }
        if working {
            commandPending = true
            queuedAction = { [weak self] in
                guard let self else { return }
                self.commandPending = false
                self.download(path, captureName:captureName)
            }
            return
        }
        error = nil; downloading = path
        request(["op":"image", "path":path]) { [weak self] data in
            guard let self else { return }
            do {
                guard data.starts(with: [137,80,78,71,13,10,26,10]) else { throw CocoaError(.fileReadCorruptFile) }
                let label = (captureName ?? self.state.capture_name ?? "").components(separatedBy: CharacterSet.alphanumerics.inverted).filter { !$0.isEmpty }.joined(separator: "-")
                let name = (label.isEmpty ? "" : label + "__") + path.components(separatedBy: "/").filter { !$0.isEmpty && $0 != "files" }.joined(separator: "__")
                try data.write(to: self.directory.appendingPathComponent(name), options: .atomic)
                self.loadImages(); self.downloading = nil
            } catch { self.fail("Could not save image: \(error.localizedDescription)") }
        }
    }
}
