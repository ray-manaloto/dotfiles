// swift-tools-version: 6.2
import PackageDescription

let package = Package(
  name: "jbax",
  platforms: [.macOS(.v15)],
  targets: [
    // The commands, so tests drive them in-process; the executable only prints and exits.
    .target(name: "JBAXKit"),
    .executableTarget(name: "jbax", dependencies: ["JBAXKit"]),
    .testTarget(name: "JBAXKitTests", dependencies: ["JBAXKit"]),
  ],
  swiftLanguageModes: [.v6]
)
