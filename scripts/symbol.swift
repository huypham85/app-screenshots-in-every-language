import AppKit
// symbol.swift <name> <pointSize> <weight: thin|regular|semibold> <out.png>  -> black symbol on transparent
let a = CommandLine.arguments
let weights: [String: NSFont.Weight] = ["thin": .thin, "regular": .regular, "semibold": .semibold]
let cfg = NSImage.SymbolConfiguration(pointSize: CGFloat(Double(a[2])!), weight: weights[a[3]] ?? .regular)
guard let base = NSImage(systemSymbolName: a[1], accessibilityDescription: nil)?.withSymbolConfiguration(cfg) else { fatalError("no symbol \(a[1])") }
let size = base.size
let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(size.width), pixelsHigh: Int(size.height), bitsPerSample: 8,
  samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
base.draw(in: NSRect(origin: .zero, size: size))
NSGraphicsContext.restoreGraphicsState()
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[4]))
print(a[1], size)
