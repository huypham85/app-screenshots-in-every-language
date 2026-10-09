---
name: appshotkit-compose
description: Build NEW App Store screenshots (iPhone 6.9", 1290×2796) for an iOS app from real captures of the app running in the iOS Simulator — gradient background, two-colour headline, device frame, floating card lifted from the UI — rendered with headless Chrome, then produced in every language the app supports. Learns the look from the app's existing store screenshots or asks for brand colours. Also adds overlays such as laurel "5-star reviews" badges to an existing screenshot. Use whenever someone wants App Store screenshots made for their app or a feature ("make App Store screenshots", "create a screenshot for our new feature", "store images for my iOS app in all languages", "add a rating badge to the first screenshot"). To only translate existing flat PNGs use appshotkit-localize.
---

# appshotkit-compose

Pipeline: **idea** → **real capture on the simulator** → **HTML frame** → **PNG** → **every locale**.
Run everything yourself and show the user the PNGs; reply in their language.

Scripts: `S=${CLAUDE_PLUGIN_ROOT}/scripts`; templates: `${CLAUDE_PLUGIN_ROOT}/templates`.
`PY=$(bash "$S/setup.sh" | tail -1)` once (needs Python 3, Google Chrome, Xcode for captures). The
first run creates a virtualenv in `~/.cache/appshotkit/venv` and installs Pillow, NumPy, OpenCV and
fontTools there — tell the user.
Formats: `${CLAUDE_PLUGIN_ROOT}/references/compose-format.md`.

```
appshots/
  brand.json                 look of the set
  compose/frames.json        frames: template, captures, crops, copy keys
  compose/copy/<locale>.json marketing copy
  captures/<locale>/*.png    simulator captures
  source/<id>.png            base-language finals;  out/<locale>/<id>.png  others
  compose/build/             generated HTML per frame/locale (git-ignore it and out/)
```

## 1. Agree on the idea

Ask what the frame should sell, then pitch 2–3 concepts (which screen, what floats out of the
phone, the headline). Consider what the existing set already says (one message per frame) and the
store order (the first three frames do most of the converting). Read
`${CLAUDE_PLUGIN_ROOT}/references/apple-rules.md` before using any Apple name, icon, badge, rating
or Siri UI. Get a yes on concept and base-language headline before building.

## 2. Brand

Skip this when `appshots/brand.json` already exists — reuse it so new frames match the set.
- The app has store screenshots already: `$PY $S/learn_brand.py <shots…> --out appshots/brand.json`,
  then render one frame and compare it side by side with the originals; adjust until it matches.
- No screenshots: ask for primary/accent colour and a light/dark preference; offer the app's
  `AccentColor` from its asset catalog as a start. Write `brand.json`.

## 3. Capture the real app

Default: capture what the simulator shows. Ask the user to put the app in the state they want
(sample data entered), then `xcrun simctl io <udid> screenshot appshots/captures/<locale>/<name>.png`.
For other languages relaunch with `-AppleLanguages "(ja)" -AppleLocale ja_JP`.

If shots must be repeatable or every locale needs localized data, offer a DEBUG-only scenario loader
in their app — only with their OK, see `${CLAUDE_PLUGIN_ROOT}/references/scenario-loader.md`.
Either way follow its capture checklist (booted simulator only, Dynamic Type `large` then restore,
status bar 9:41, wait for async work, look at every capture).

## 4. Compose

1. Describe the frame in `compose/frames.json` (template `phone`, `phone-card`, or a new HTML file
   you add next to the templates for a special layout). Crop the floating card from a capture by
   pixel-scanning for the card's edges — layouts shift between languages, so give per-locale crops.
2. Write `compose/copy/<base>.json` (base = `base_locale` in brand.json, default `en`), then
   `$PY $S/compose.py --root appshots --locale <base> --only <id>`.
3. Check, and look at every image yourself:
   - `$PY $S/compare.py preview appshots/source/<id>.png /tmp/p.png` (50 %),
   - edges and dense areas: `$PY $S/measure.py crop appshots/source/<id>.png x0 y0 x1 y1 /tmp/c.png`,
   - next to the rest of the set: `$PY $S/compare.py set appshots /tmp/set.png`.
   Iterate on brand/frame until it looks like it belongs to the set.

Layout tips: in `phone` (no card) the phone should fill the frame — move it down and let it bleed
off the bottom (`"style": {"extra_css": ".phone { top: 900px; }"}`) instead of leaving a bare band.
Make the frame show what the headline promises: zoom into that part of the UI with a floating card
rather than repeating the same screen as another frame.

Laurels/badges on an existing frame: render SF Symbols on the Mac
(`swift $S/symbol.swift laurel.leading 300 thin appshots/assets/laurel_l.png`, same for
`laurel.trailing`), then an `overlay-badges` frame with `onto` pointing at a badge-free copy of
that screenshot (keep it in `source/_base/`). To remove something from an existing PNG first,
fill the area with a surface fit of the surrounding gradient and feather the edge; check at high
contrast that no rectangle shows.

## 5. Localize

- Which locales: the app's own (`$PY $S/xcstrings.py --root <repo> --locales`). Skip a frame where
  its feature doesn't exist (language-gated features; Apple features per apple-rules.md).
- Captures per locale: same states, relaunched in that language.
- Copy per locale in `compose/copy/<locale>.json`: native marketing copy, never word for word.
  UI words that appear in your copy should match the app's own wording — `xcstrings.py` when the
  repo has String Catalogs, otherwise its `.strings` files or the captures themselves. Show the user
  the headlines before building everything.
- `$PY $S/compose.py --root appshots --all-locales --only <id>` (leave `--only` off only to rebuild
  the whole set). Long lines shrink automatically; Arabic/Hebrew get `dir="rtl"`; Chrome uses the
  Mac's system fonts for CJK/Arabic/Devanagari, as iOS does.
- QA: `$PY $S/compare.py set appshots /tmp/set.png vi ja ar …` and zooms on RTL, CJK, long
  German/Russian lines, and stacked diacritics (Vietnamese) touching the line above.
- Fixes for one language go in its copy file, not the frame:
  `"_style": {"<id>": {"extra_css": ".headline { line-height: 1.08; }"}}`.

## 6. Finish
Report paths, which text came from the app vs. what you wrote, and any Apple-rule risks left open.
Commit the inputs (`brand.json`, `compose/` without `compose/build/`, `captures/`, `source/`);
`out/` and `compose/build/` are generated (the plugin's own demo keeps `out/` only as a showcase).
Example to copy: `${CLAUDE_PLUGIN_ROOT}/examples/demo/appshots/`.
