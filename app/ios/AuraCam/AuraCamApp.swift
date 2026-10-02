import SwiftUI
import Photos

@main struct AuraCamApp: App {
    @StateObject private var radio = RadioLink()
    var body: some Scene { WindowGroup { ContentView().environmentObject(radio).preferredColorScheme(.light) } }
}
private let paper = Color(red: 0.95, green: 0.94, blue: 0.90)
struct Portal: View {
    var body: some View {
        Canvas { context, size in
            context.fill(Path(CGRect(origin: .zero, size: size)), with: .color(.black))
            for i in 0..<19 {
                let t = CGFloat(i)/18
                var path = Path()
                for j in 0...120 {
                    let x = CGFloat(j)/120
                    let wave = sin(x * .pi * 2.0 + t * 1.5)
                    let y = size.height * (0.12 + t * 0.69 + wave * 0.11 * sin(t * .pi))
                    if j == 0 { path.move(to: CGPoint(x: x * size.width, y: y)) }
                    else { path.addLine(to: CGPoint(x: x * size.width, y: y)) }
                }
                context.stroke(path, with: .color(paper.opacity(0.8)), lineWidth: i % 5 == 0 ? 2 : 0.65)
            }
            let doorway = CGRect(x: size.width*0.43, y: size.height*0.34, width: size.width*0.14, height: size.height*0.47)
            context.fill(Path(doorway), with: .color(paper))
            var shadow = Path(); shadow.move(to: CGPoint(x: doorway.minX,y: doorway.maxY)); shadow.addLine(to: CGPoint(x: doorway.maxX,y: doorway.maxY)); shadow.addLine(to: CGPoint(x: size.width*0.83,y: size.height)); shadow.addLine(to: CGPoint(x: size.width*0.51,y: size.height)); shadow.closeSubpath()
            context.fill(shadow, with: .color(paper))
        }.accessibilityLabel("An open doorway through curved radio lines")
    }
}
struct InkButton: ButtonStyle {
    @Environment(\.isEnabled) var enabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.system(size: 12, weight: .medium, design: .monospaced)).tracking(1.2)
            .frame(maxWidth: .infinity).padding(.vertical,18)
            .foregroundStyle(paper).background(Color.black.opacity(enabled ? (configuration.isPressed ? 0.65 : 1) : 0.3))
    }
}
struct ContentView: View {
    @EnvironmentObject var radio: RadioLink
    @State private var section = 0
    @State private var settings = false
    @State private var confirm = false
    @State private var selected: LocalImage?
    @State private var captureName = ""
    @State private var nameSaved = false
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    HStack(alignment: .top) {
                        VStack(alignment: .leading,spacing:4) {
                            Text("AURA / CAM").font(.system(size:28,weight:.black,design:.serif)).tracking(-1)
                            Text("AN INSTRUMENT FOR THE UNSEEN").font(.system(size:8,design:.monospaced)).tracking(1.3)
                        }
                        Spacer()
                        Button { settings = true } label: { Image(systemName:"slider.horizontal.3").padding(12) }.accessibilityLabel("Render settings")
                    }
                    HStack(spacing:5) { Circle().fill(radio.ready ? Color.black : Color.gray).frame(width:5,height:5); Text(radio.status.uppercased()).font(.system(size:9,design:.monospaced)).tracking(1) }
                    HStack {
                        tab("01  CAPTURE",0); Spacer(); tab("02  LIBRARY",1); Spacer(); tab("03  SAVED",2)
                    }.padding(.vertical,12).overlay(alignment:.bottom){Rectangle().frame(height:1)}
                    if section == 0 { capture }
                    if section == 1 { CaptureLibraryView().environmentObject(radio) }
                    if section == 2 { collection }
                    if let error = radio.error { Text(error).font(.system(size:12,design:.monospaced)).padding().frame(maxWidth:.infinity,alignment:.leading).overlay(Rectangle().stroke(lineWidth:1)) }
                    Text("RADIO BECOMES FORM.\nNO CAMERA. NO TWO FIELDS ALIKE.").font(.system(size:9,design:.monospaced)).tracking(1).lineSpacing(5).foregroundStyle(.secondary).padding(.vertical,16)
                }.padding(24)
            }.background(paper).foregroundStyle(.black)
                .onChange(of:radio.state.capture_id) { _,_ in captureName = ""; nameSaved = false }
                .onChange(of:radio.nameSaveRevision) { _,_ in nameSaved = true; captureName = ""; section = 1 }
                .onChange(of:radio.downloading) { _, value in UIApplication.shared.isIdleTimerDisabled = value != nil }
                .sheet(isPresented:$settings) { SettingsView().environmentObject(radio) }
                .sheet(item:$selected) { ImageDetail(item:$0) }

        }.tint(.black)
    }
    func tab(_ label:String,_ index:Int)->some View {
        Button {section=index} label:{Text(label).font(.system(size:9,weight:section==index ? .bold : .regular,design:.monospaced)).opacity(section==index ? 1 : 0.5)}.padding(.vertical,6)
    }
    var capture: some View {
        VStack(alignment:.leading,spacing:20) {
            Portal().frame(height:210)
            Text(radio.state.busy ? "The field\nis listening." : "Step into\nthe invisible.").font(.system(size:43,weight:.regular,design:.serif)).tracking(-2).lineSpacing(-3)
            Text(radio.state.message).font(.system(size:13)).lineSpacing(4)
            if let status = radio.commandStatus { HStack { ProgressView(); Text(status).font(.system(size:12,design:.monospaced)) } }
            if let error = radio.error { Text(error).font(.system(size:12)).foregroundStyle(.red) }
            if !radio.ready {
                ForEach(radio.devices,id:\.identifier) { p in Button("CONNECT / \(p.name ?? "AuraCam Pi")") {radio.connect(p)}.buttonStyle(InkButton()) }
                if radio.devices.isEmpty {Button("FIND INSTRUMENT") {radio.scan()}.buttonStyle(InkButton())}
            } else if radio.state.busy || radio.countdown != nil {
                if let n=radio.countdown ?? radio.state.remaining,n>0 { Text(String(format:"%02d",n)).font(.system(size:64,weight:.light,design:.monospaced)) }
                ProgressView().tint(.black)
            } else {
                controls.disabled(radio.commandPending || radio.downloading != nil)
            }
            if let frequency=radio.state.center_hz {
                Text(String(format:"LOCKED / %.2f MHz",Double(frequency)/1e6)).font(.system(size:10,design:.monospaced))
            }
        }
    }
    @ViewBuilder var controls: some View {
        if radio.state.stage == "gallery" { naming }
        if radio.state.stage == "choose" {
            ForEach(radio.state.candidates) { band in
                Button {radio.action("tune",extra:["center_hz":band.center_hz])} label:{
                    HStack {Text(String(format:"%.2f MHz",Double(band.center_hz)/1e6));Spacer();Text(String(format:"σ %.3f dB",band.variation_db));Image(systemName:"arrow.right")}.font(.system(size:12,design:.monospaced)).padding(.vertical,18)
                }.overlay(alignment:.bottom){Rectangle().frame(height:0.5)}
            }
            Text("Ranked by strength and stability. Select a band to lock it.").font(.caption)
        }
        if ["ready","baseline_review","locked","gallery"].contains(radio.state.stage) {
            if ["locked","gallery"].contains(radio.state.stage) { Button("CAPTURE  →") {radio.prepare("capture")}.buttonStyle(InkButton()) }
            if radio.state.stage == "baseline_review" {
                if let b=radio.state.baseline { Text(String(format:"BASELINE / σ %.3f dB · %d readings",b.variation_db,b.samples)).font(.system(size:10,design:.monospaced)) }
                Button("LOCK BASELINE") {radio.action("lock")}.buttonStyle(InkButton())
            }
            Button("MEASURE / RESCAN BASELINE") {radio.prepare("baseline")}.buttonStyle(InkButton())
        }
        if confirm {
            VStack(alignment:.leading,spacing:12) {
                Text("START A NEW SESSION?").font(.system(size:12,weight:.bold,design:.monospaced))
                Text("This replaces the active baseline. Saved images stay on the Pi.").font(.caption)
                Button("CONFIRM / SCAN FREQUENCIES") {confirm=false;radio.action("survey")}.buttonStyle(InkButton())
                Button("Cancel") {confirm=false}.frame(maxWidth:.infinity).padding(10)
            }.padding(16).overlay(Rectangle().stroke(lineWidth:1))
        } else {
            Button("START NEW SESSION") {confirm=true}.buttonStyle(InkButton())
        }
    }
    var naming: some View {
        VStack(alignment:.leading,spacing:12) {
            Text(nameSaved ? "NAME SAVED ✓" : "NAME THIS CAPTURE").font(.system(size:10,design:.monospaced))
            Text(radio.state.capture_name ?? "Unnamed capture").font(.system(size:24,design:.serif))
            Text("CAPTURE / " + (radio.state.capture_id?.replacingOccurrences(of:"guest-",with:"") ?? "—")).font(.system(size:10,design:.monospaced))
            TextField(radio.state.capture_name ?? "Leave blank for a generated name",text:$captureName)
                .textInputAutocapitalization(.words).padding(12).overlay(Rectangle().stroke(lineWidth:1))
            Text("Enter a name, or keep the name shown above.").font(.caption)
            Button(captureName.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty ? "KEEP NAME & VIEW IMAGES →" : "SAVE NAME & VIEW IMAGES →") {
                nameSaved = false
                radio.action("name",extra:["capture_id":radio.state.capture_id ?? "","name":captureName])
            }.buttonStyle(InkButton()).disabled(!radio.ready || radio.commandPending || radio.downloading != nil || radio.state.busy)
        }
    }
    var remoteGallery: some View {
        VStack(alignment:.leading,spacing:18) {
            Text("Field studies.").font(.system(size:36,design:.serif))
            if radio.awaitingCapture || ["capturing","calibrating","surveying"].contains(radio.state.stage) {
                Text("NEW CAPTURE IN PROGRESS").font(.system(size:12,design:.monospaced))
                Text("Previous images are hidden until the new set is ready.").font(.caption)
                ProgressView()
            } else if radio.state.capture_id != nil {
                Text("LATEST COMPLETED CAPTURE").font(.system(size:10,design:.monospaced))
                naming
                Text("3 EMPTY BASELINES + 3 PRESENCE TREATMENTS").font(.system(size:9,design:.monospaced))
            }
            Text("Download an original to keep and share. Keep the app open during Bluetooth transfers.").font(.system(size:13)).lineSpacing(4)
            if radio.state.gallery.isEmpty {Text("Your baseline and guest treatments will appear here.").font(.caption)}
            ForEach((radio.awaitingCapture || ["capturing","calibrating","surveying"].contains(radio.state.stage)) ? [] : radio.state.gallery,id:\.self) { path in
                VStack(alignment:.leading,spacing:12) {
                    Text(path.contains("/presence-") ? "PRESENCE / THIS CAPTURE" : "EMPTY / BASELINE PARTNER").font(.system(size:9,design:.monospaced)).foregroundStyle(.secondary)
                    Text(path.components(separatedBy:"/").last?.replacingOccurrences(of:".png",with:"").uppercased() ?? "ARTWORK").font(.system(size:12,design:.monospaced))
                    if radio.downloading == path {ProgressView(value:radio.progress);Text("\(Int(radio.progress*100))% / RECEIVING ORIGINAL").font(.system(size:9,design:.monospaced))}
                    Button("DOWNLOAD TO IPHONE ↓") {radio.download(path)}.buttonStyle(InkButton()).disabled(!radio.ready || radio.commandPending || radio.downloading != nil)
                }.padding(.vertical,8)
            }
        }
    }
    var collection: some View {
        VStack(alignment:.leading,spacing:18) {
            Text("Collected\nfrom the air.").font(.system(size:36,design:.serif))
            Text("Stored on this iPhone. Open an image to save to Photos or share with a guest.").font(.system(size:13)).lineSpacing(4)
            if radio.images.isEmpty {Text("No downloads yet.").font(.system(size:12,design:.monospaced))}
            LazyVGrid(columns:[GridItem(.flexible()),GridItem(.flexible())],spacing:16) {
                ForEach(radio.images) {item in
                    Button {selected=item} label:{VStack(alignment:.leading){if let image=UIImage(contentsOfFile:item.url.path){Image(uiImage:image).resizable().scaledToFit()};Text(item.captureName).font(.system(size:11,weight:.medium));Text(item.name.uppercased()).font(.system(size:8,design:.monospaced)).lineLimit(2)}}
                }
            }
        }
    }
}
struct SettingsView: View {
    @EnvironmentObject var radio: RadioLink
    @Environment(\.dismiss) var dismiss
    @State var dark=true
    @State var color=0.0
    @State var format=0
    @State var ribbons=1.1
    @State var terrain=1.4
    @State var twist=1.0
    var body: some View {
        NavigationStack {Form {
            Section("Artwork") {Toggle("Black background",isOn:$dark);VStack(alignment:.leading){Text("Chromatic color / \(Int(color*100))%");Slider(value:$color,in:0...1)};Picker("Export",selection:$format){Text("Portrait post · 1080 × 1350").tag(0);Text("Square · 1080 × 1080").tag(1);Text("Story · 1080 × 1920").tag(2)}}
            DisclosureGroup("Advanced amplitude") {
                Text("Empty baselines stay at 0.20×.").font(.caption)
                Text(String(format:"Harmonic ribbons %.2f×",ribbons));Slider(value:$ribbons,in:0.2...2)
                Text(String(format:"Spectral terrain %.2f×",terrain));Slider(value:$terrain,in:0.2...2)
                Text(String(format:"Twisted field %.2f×",twist));Slider(value:$twist,in:0.2...2)
            }
            Section {Text("Applies to the next baseline or guest capture. Each guest includes a minimal baseline and three presence treatments. Existing downloads stay unchanged.").font(.caption)
                Button("APPLY TO NEXT CAPTURE") {radio.action("settings",extra:["dark":dark,"chroma":color,"size":[1080,[1350,1080,1920][format]],"gains":["ribbons":ribbons,"terrain":terrain,"twist":twist]]);dismiss()}.disabled(!radio.ready || radio.commandPending || radio.downloading != nil || radio.state.busy)
            }
        }.onAppear {
            if let saved=radio.state.render_settings {
                dark=saved.dark;color=saved.chroma;format=[1350,1080,1920].firstIndex(of:saved.size.last ?? 1350) ?? 0
                ribbons=saved.gains?["ribbons"] ?? 1.1;terrain=saved.gains?["terrain"] ?? 1.4;twist=saved.gains?["twist"] ?? 1.0
            }
        }.navigationTitle("Render settings").toolbar{Button("Done"){dismiss()}}.tint(.black)
        }
    }
}
struct ShareSheet: UIViewControllerRepresentable {
    let url:URL
    func makeUIViewController(context:Context)->UIActivityViewController {UIActivityViewController(activityItems:[url],applicationActivities:nil)}
    func updateUIViewController(_ uiViewController:UIActivityViewController,context:Context){}
}
struct ImageDetail: View {
    let item:LocalImage
    @State var share=false
    @State var message=""
    @Environment(\.dismiss) var dismiss
    var body:some View {
        NavigationStack {ScrollView {VStack(spacing:20){
            if let image=UIImage(contentsOfFile:item.url.path){Image(uiImage:image).resizable().scaledToFit()}
            Button("SHARE / AIRDROP / MESSAGES") {share=true}.buttonStyle(InkButton())
            Button("SAVE TO PHOTOS") {save()}.buttonStyle(InkButton())
            Text(message).font(.caption)
        }.padding(24)}.background(paper).navigationTitle(item.captureName).navigationBarTitleDisplayMode(.inline).toolbar{Button("Done"){dismiss()}}.sheet(isPresented:$share){ShareSheet(url:item.url)}
        }
    }
    func save(){PHPhotoLibrary.requestAuthorization(for:.addOnly){status in
        guard status == .authorized || status == .limited else {DispatchQueue.main.async{message="Allow Photos access in Settings to save."};return}
        PHPhotoLibrary.shared().performChanges({PHAssetChangeRequest.creationRequestForAssetFromImage(atFileURL:item.url)}) {success,error in DispatchQueue.main.async{message=success ? "Saved to Photos." : error?.localizedDescription ?? "Could not save."}}
    }}
}

struct CaptureLibraryView: View {
    @EnvironmentObject var radio: RadioLink
    @State private var deleteTarget: CaptureEntry?
    @State private var confirmDelete = false
    var body: some View {
        VStack(alignment:.leading,spacing:20) {
            Text("The collection.").font(.system(size:36,design:.serif))
            Text("CAPTURES STORED ON YOUR PI").font(.system(size:10,design:.monospaced))
            Text("Open a name to download or share its images. Saved on iPhone contains your offline copies.").font(.system(size:13)).lineSpacing(4)
            Button(radio.libraryBusy ? "LOADING…" : "REFRESH LIBRARY") {radio.loadLibrary()}.buttonStyle(InkButton()).disabled(!radio.ready || radio.libraryBusy || radio.commandPending || radio.downloading != nil)
            if !radio.ready {Text("Connect to your instrument to load the library.").font(.caption)}
            if radio.libraryLoaded && radio.library.isEmpty {Text("No completed captures on the Pi yet.").font(.caption)}
            ForEach(radio.library) { entry in
                HStack(alignment:.top,spacing:16) {
                    NavigationLink {CaptureDetailView(entry:entry).environmentObject(radio)} label:{
                        VStack(alignment:.leading,spacing:8) {
                            Text(entry.name).font(.system(size:25,design:.serif))
                            Text(entry.date.formatted(date:.abbreviated,time:.shortened)).font(.system(size:11,design:.monospaced))
                            Text("6 IMAGES / " + String(entry.id.split(separator:"/").last ?? "")).font(.system(size:8,design:.monospaced)).foregroundStyle(.secondary)
                        }.frame(maxWidth:.infinity,alignment:.leading)
                    }.foregroundStyle(.black)
                    Button {deleteTarget=entry;confirmDelete=true} label:{Image(systemName:"trash").padding(12)}.accessibilityLabel("Delete \(entry.name) from Pi").disabled(!radio.ready || radio.commandPending || radio.state.busy || radio.downloading != nil)
                }.padding(.vertical,14).overlay(alignment:.bottom){Rectangle().frame(height:0.5)}
            }
        }.onAppear {radio.loadLibrary()}
        .confirmationDialog("Delete \(deleteTarget?.name ?? "this capture") from the Pi? Its measurements and six images will be removed. Downloaded iPhone copies stay saved.",isPresented:$confirmDelete,titleVisibility:.visible) {
            Button("Delete from Pi",role:.destructive) {if let entry=deleteTarget {radio.deleteCapture(entry)};deleteTarget=nil}
            Button("Cancel",role:.cancel){deleteTarget=nil}
        }
    }
}
struct CaptureDetailView: View {
    let entry:CaptureEntry
    @EnvironmentObject var radio:RadioLink
    @State private var selected:LocalImage?
    func local(_ path:String)->LocalImage? {
        let suffix=path.components(separatedBy:"/").filter{!$0.isEmpty && $0 != "files"}.joined(separator:"__")
        return radio.images.first{$0.url.lastPathComponent.hasSuffix(suffix)}
    }
    var body:some View {
        ScrollView {
            VStack(alignment:.leading,spacing:22) {
                Text(entry.name).font(.system(size:36,design:.serif))
                Text(entry.date.formatted(date:.abbreviated,time:.shortened)).font(.system(size:12,design:.monospaced))
                Text(entry.id).font(.system(size:9,design:.monospaced)).foregroundStyle(.secondary)
                Text("Three baseline partners and three presence treatments. Download an image to preview, save, or share it.").font(.system(size:13))
                ForEach(entry.images,id:\.self) {path in
                    VStack(alignment:.leading,spacing:12) {
                        Text((path.components(separatedBy:"/").last ?? "").replacingOccurrences(of:".png",with:"").uppercased()).font(.system(size:11,design:.monospaced))
                        if let item=local(path),let image=UIImage(contentsOfFile:item.url.path) {
                            Button {selected=item} label:{Image(uiImage:image).resizable().scaledToFit()}
                            Button("OPEN / SHARE") {selected=item}.buttonStyle(InkButton())
                            Text("SAVED ON THIS IPHONE").font(.system(size:9,design:.monospaced))
                        } else {
                            if radio.downloading==path {ProgressView(value:radio.progress);Text("\(Int(radio.progress*100))% RECEIVED").font(.caption)}
                            Button("DOWNLOAD TO IPHONE ↓") {radio.download(path,captureName:entry.name)}.buttonStyle(InkButton()).disabled(!radio.ready || radio.commandPending || radio.downloading != nil)
                        }
                    }
                }
                if let error=radio.error {Text(error).font(.caption)}
            }.padding(24)
        }.background(paper).foregroundStyle(.black).navigationTitle("Capture").navigationBarTitleDisplayMode(.inline)
        .sheet(item:$selected){ImageDetail(item:$0)}
    }
}
