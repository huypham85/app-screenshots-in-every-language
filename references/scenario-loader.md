# Fake app state for screenshots (optional, needs the user's OK)

Default: capture whatever the simulator shows — the user fills in sample data by hand. That needs
no code, but the data is not repeatable and user-entered text stays in one language.

With the user's permission, add a **DEBUG-only scenario loader** to their app. It reads a JSON file
passed as a launch argument and fills an in-memory store, so real data is never touched and every
locale can be shot unattended. Never put it outside `#if DEBUG`.

## Shape

```swift
#if DEBUG
struct ScreenshotScenario: Decodable {
    // mirror the app's own models, only what the shots need
    let items: [Item]
    struct Item: Decodable { let title: String; let done: Bool }

    static func load() -> ScreenshotScenario? {
        guard let path = UserDefaults.standard.string(forKey: "screenshotScenario") else { return nil }
        let data = try! Data(contentsOf: URL(fileURLWithPath: path))
        return try! JSONDecoder().decode(Self.self, from: data)
    }
}
#endif
```

Launch: `xcrun simctl launch booted <bundle id> -screenshotScenario /abs/path/scenario.json`
(launch arguments become UserDefaults values). Add `-AppleLanguages "(ja)" -AppleLocale ja_JP`
to shoot another language.

## Wire it into the store the app already uses

- **SwiftData**: at the point the app builds its `ModelContainer`, return
  `ModelContainer(for: schema, configurations: [ModelConfiguration(isStoredInMemoryOnly: true)])`
  when a scenario is present, then insert the models. Insert an object before assigning its
  relationships (iOS 17 asserts otherwise).
- **Core Data**: an `NSPersistentContainer` with a `/dev/null` store URL (in-memory), seeded the same way.
- **UserDefaults / files**: use a separate suite or temp directory when a scenario is present.
- **Network-backed apps**: stub the API client behind a protocol, return scenario data.
- **System integrations** (HealthKit, contacts, location): put the real service behind a protocol
  and swap in a fake that returns the same value types, so the app's own logic still runs.

Screens reached by taps: add a scenario field that opens them at launch (e.g. `"openScreen":
"import-review"`) so every locale is shot without driving the UI.

## Capture checklist
- Use the booted simulator the user already has; don't boot others.
- Read `xcrun simctl ui <udid> content_size` first; shoot at `large`; restore the user's value.
- `xcrun simctl status_bar <udid> override --time 9:41 --batteryState charged --batteryLevel 100
  --cellularBars 4 --wifiBars 3`, then `status_bar <udid> clear` at the end.
- Light mode unless asked: `xcrun simctl ui <udid> appearance light`.
- Wait for async work before `xcrun simctl io <udid> screenshot out.png`; look at every capture.
- System alerts on the simulator: dismiss with the non-committal option only ("Not Now").
