import Foundation
struct Band: Codable, Identifiable {
    var center_hz: Int; var power_db: Double; var variation_db: Double
    var id: Int { center_hz }
}
struct Baseline: Codable { var id: String; var variation_db: Double; var samples: Int }
struct RenderSettings: Codable {
    var dark: Bool
    var chroma: Double
    var size: [Int]
    var gains: [String: Double]?
}
struct RadioState: Codable {
    var stage: String = "idle"
    var busy: Bool = false
    var message: String = "Connect to your instrument to begin."
    var candidates: [Band] = []
    var gallery: [String] = []
    var remaining: Int?
    var capture_id: String?
    var capture_name: String?
    var center_hz: Int?
    var baseline: Baseline?
    var render_settings: RenderSettings?
}
struct LocalImage: Identifiable {
    let url: URL
    var id: String { url.lastPathComponent }
    var captureName: String { let parts = url.lastPathComponent.components(separatedBy: "__"); return parts.count >= 4 ? parts[0].replacingOccurrences(of: "-", with: " ") : "Field study" }
    var name: String { url.deletingPathExtension().lastPathComponent.components(separatedBy: "__").last ?? "Capture" }
}

struct CaptureEntry: Codable, Identifiable {
    var id: String
    var name: String
    var timestamp: Double
    var images: [String]
    var date: Date { Date(timeIntervalSince1970:timestamp) }
}
