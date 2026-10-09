# app-screenshots-in-every-language — design notes

Author: Huy Pham ([@huyphamm85](https://x.com/huyphamm85) on X, huypham85 on GitHub). Extracted from the screenshot pipeline built for the Doz iOS app.

## Goal
Let any iOS developer using Claude Code (a) build App Store screenshots from real captures of their
app and (b) localize screenshots into every language they support — without a design tool.
Success: a developer with an app and a simulator gets a store-ready, on-brand frame in their base
language and its translations in one session.

## Decisions (v0.1)
- **Distribution**: a Claude Code plugin; the repo is its own marketplace (MIT, personal GitHub).
- **Two skills, one shared `scripts/`**: `make-app-screenshots` (new frames) and `localize-app-screenshots`
  (text-only translation of flat PNGs). Shared core avoids duplicated rendering code.
- **Scope**: iPhone 6.9" (1290×2796) only — the size App Store Connect requires; smaller iPhone
  sizes are scaled from it. iPad and Google Play later.
- **Look**: `brand.json`. Learned from existing screenshots (`learn_brand.py`) when the app has
  them, otherwise asked. Templates read it as CSS variables.
- **App state**: capture what the simulator shows by default; a DEBUG-only scenario loader in the
  user's app is offered, never added without consent.
- **Nothing proprietary is bundled**: no SF Pro (used if installed; Inter OFL bundled), no Apple
  icons or SF Symbols images (generated on the user's Mac), no Doz assets. The device frame is CSS.
- **Copy sources**: UI words from the app's `.xcstrings`; marketing copy written per language by
  Claude and shown to the user.

## Components
| Part | Role |
|---|---|
| `scripts/shotloc.py`, `build.py`, `measure.py`, `compare.py` | text-only localization engine + QA |
| `scripts/compose.py`, `templates/*.html`, `base.css` | frame builder (HTML → PNG per locale) |
| `scripts/learn_brand.py` | measure colours/sizes from existing screenshots |
| `scripts/xcstrings.py`, `timefmt.swift` | app's own translations, iOS time/date formats |
| `scripts/render.sh`, `symbol.swift`, `setup.sh` | headless Chrome render, SF Symbol export, venv |
| `references/` | file formats, scenario loader guide, Apple rules |
| `examples/demo/` | fictional habit tracker: compose (en, vi, ja, ar) + localize (de) |

## Known limits
Text-only localization does not mirror RTL layouts. Crops for floating cards are per-locale
coordinates. Apple guideline risks (icons, Siri UI, generic device look) are documented, not solved.
