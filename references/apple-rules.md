# Apple rules that touch App Store screenshots

Summaries with links; re-read the source before relying on a detail, they change. Not legal advice.

## Accurate metadata — App Review Guidelines 2.3
<https://developer.apple.com/app-store/review/guidelines/#accurate-metadata>
- Screenshots must reflect the app's core experience; misleading marketing can get an app removed
  (2.3.1). Show the app in use, not just title art (2.3.3).
- Ratings are shown per storefront. A number in a frame ("4.9★") can contradict the rating right
  above it in some countries; wording without a number ("5-star reviews") holds everywhere.

## Marketing guidelines — <https://developer.apple.com/app-store/marketing/guidelines/>
- Don't use icons, logos or images from apple.com to promote your app; use only Apple's badge
  artwork. Apple app icons (Siri, Shortcuts, Health…) placed outside the phone screen are a risk.
- Apps working inside Siri/Messages/Maps: show the Apple UI *exactly* as it appears when the app runs
  — prefer a real capture over a redrawn Siri card.
- Apple trademarks (Siri, Apple Pay…) keep their capital letter and are not translated.
- Illustrations of generic devices must not include details unique to Apple products. The CSS
  frame in `templates/` resembles a modern iPhone; if that matters to you, use Apple's official
  device bezels (Apple Design Resources) instead.
- Use fictional data, never a real person's.

## Apple Health — <https://developer.apple.com/licensing-trademarks/works-with-apple-health/>
- The Health app icon is permitted in your app's UI; outside it, use the "Works with Apple Health"
  badge (Apple's artwork only, no effects, one per promotion, ≥30px tall).
- Say "the Apple Health app" / "the Health app from Apple"; never "Apple Health data".

## Feature availability by language — <https://www.apple.com/ios/feature-availability/>
- Before making a frame about an Apple feature (Siri, Apple Intelligence…) for a locale, check the
  feature exists in that language. Example: Siri in India is English-only, so no Hindi Siri frame.
- Same for the app's own features: a feature gated to some languages gets no frame elsewhere.

## Fonts
- SF Pro is licensed for creating mockups of Apple-platform UI; this kit never bundles it and uses
  it only when installed (developer.apple.com/fonts). Inter (OFL) is the bundled fallback.
- SF Symbols images (e.g. laurels) are generated on the user's Mac with `symbol.swift`, not shipped.
