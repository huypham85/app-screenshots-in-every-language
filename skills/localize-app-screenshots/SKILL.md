---
name: localize-app-screenshots
description: Translate the TEXT of existing App Store screenshot PNGs (iPhone 6.9", e.g. exported from Figma or made by a designer) into other languages while keeping everything else pixel-identical — erase each text, redraw the translation with matched font, size, colour and baseline, resize tags and pills, keep two-colour headlines, handle CJK, Arabic (RTL) and Devanagari. Use whenever someone wants their App Store screenshots in another language ("localize my screenshots", "translate screenshots to Japanese/German", "make store images for every locale", "only change the text, keep the design"), wants to add a screenshot to a localized set, or rebuild after copy changes. For building a NEW screenshot from simulator captures use make-app-screenshots instead.
---

# localize-app-screenshots

Turns flat screenshot PNGs (no design source) into localized PNGs. Only text changes. Everything
is deterministic Python: run the scripts yourself and show the user the results — don't hand them
commands. Reply in the user's language.

Scripts: `S=${CLAUDE_PLUGIN_ROOT}/scripts`. Get the interpreter once per session:
`PY=$(bash "$S/setup.sh" | tail -1)` — the first run creates `~/.cache/app-screenshots-in-every-language/venv` and installs
Pillow, NumPy, OpenCV and fontTools (tell the user); it prints which font will be used.
Run every command from the user's repo root; paths below start with `appshots/`.

## Folder (in the user's repo; ask if they already keep screenshots elsewhere)

```
appshots/
  source/01.png …           base-language screenshots (never modified)
  layouts/01.json …         per screenshot: where every text item is (language-independent)
  strings/<locale>.json     per locale: translations shared by all screenshots + headlines
  out/<locale>/01.png …     generated — add appshots/out/ to .gitignore
```

## Fonts and scripts
- SF Pro is used when installed (developer.apple.com/fonts), else bundled Inter (very close, not
  identical). The build prints `font=`; tell the user once. Force one with `SHOTLOC_FONTS=sf|inter`.
  If the screenshots use another typeface entirely, say so: redrawn text will be SF Pro/Inter, and
  the roundtrip (below) is where that shows.
- Non-Latin locales pick the iOS system font from `"locale"` in the strings file: ja Hiragino Sans,
  ko Apple SD Gothic Neo, zh Hiragino Sans GB (PingFang is not readable by FreeType), ar SF Arabic,
  hi SF Devanagari. Latin letters and digits stay SF Pro, as on iOS. Arabic text is laid out RTL
  inside each item; the screenshot layout itself is not mirrored — say so when delivering Arabic.
- Arabic/Devanagari need FriBiDi (`brew install fribidi`; ask before installing).

## A. Write a layout for a screenshot (once per screenshot)

Read `${CLAUDE_PLUGIN_ROOT}/references/layout-format.md` first.

1. `$PY $S/measure.py grid appshots/source/NN.png /tmp/grid.png` and view it to read coordinates
   (`$PY $S/measure.py` alone prints all subcommands; they take separate numeric arguments).
2. For every string to translate, zoom with `measure.py crop` and define a **box** around only that
   string's ink plus a few px of its own background — no icons, tag edges or neighbours. Validate
   with `measure.py box …`; fix the box if it prints a WARNING.
   - Include every legible UI word: titles, headers, chips, tags, buttons, tab bar, weekday labels,
     system strings on lock screens/notifications ("now", "Do Not Disturb").
   - A string mixing words with a number, name or date is ONE item with the full text as `src`.
   - Skip brand/product names, pure numbers/times, status bar, blurred or mostly hidden text, and
     Apple badges (Apple ships localized badge artwork — tell the user).
   - Fragments cut off by an overlay but still readable need the `clip` recipe.
   - A sentence wrapped over two lines is two items; translations must split into similar lines.
3. Tags/pills whose width depends on the text: `"pill"` from `measure.py pill src y x`.
4. Icon + label buttons: `"button"`. Repeated UI — tab bar, weekday labels, **list-row titles and
   subtitles, identical cards** — gets one `"group"` per kind so all rows share one size.
5. Headline: `src_lines` (`*accent*`, `^big^`), one `line_box` per line, `erase` box(es) that avoid
   decorations, `colors` sampled with `measure.py color`; `sizes`/`big_size` from `measure.py fit`
   when lines differ.
6. **Verify before any locale**: `$PY $S/build.py --root appshots --roundtrip --only NN` re-renders
   the base text; `$PY $S/compare.py diff appshots/source/NN.png appshots/out/_roundtrip/NN.png`
   should be ≥ 97 % identical. The number is not enough: also look at
   `$PY $S/compare.py side appshots/source/NN.png appshots/out/_roundtrip/NN.png /tmp/side.png` —
   nothing shifted, same weight and size. Fix boxes/sizes until it is.

Many screenshots: one subagent per 2 screenshots works well; give each the format doc, these rules
and the roundtrip check, and compile the strings yourself so terms stay consistent.

## B. Build locales

0. If a layout already exists, check it covers **every** text in the screenshot (headline-only
   layouts leave the UI in the base language) — add the missing items first (part A).
   Check each screenshot's feature exists in that locale (language-gated features, Apple features
   like Siri — see `${CLAUDE_PLUGIN_ROOT}/references/apple-rules.md`). Skip it where it doesn't.
1. Write `appshots/strings/<locale>.json` (below).
2. `$PY $S/build.py --root appshots --locale vi ja` (or `--all-locales`, `--only 01 03`).
3. Fix every `UNTRANSLATED KEYS` line and rebuild.
4. QA: `$PY $S/compare.py sheet appshots <locale> /tmp/sheet.png`; every output in halves at 60 %
   with `$PY $S/compare.py halves appshots/out/<locale>/NN.png /tmp/h.png`; zooms on dense areas
   with `$PY $S/measure.py crop appshots/out/<locale>/NN.png x0 y0 x1 y1 /tmp/z.png`. Look for broken diacritics/shaping, ghosts or flat patches,
   collisions, text past a tag/button/card edge. `NOTE pill … grew by Npx` lines need a look.
   Fix with layout options before rewording: `pill_anchor: "right"`, `pill` + `push` for chip rows,
   `align: "right"`, `erase: "fit"` on glows, `clip`/`fade` under overlays, a slightly smaller `size`.
   Fixes for one locale only go in its strings file:
   `"layout_overrides": {"NN": {"<item key>": {"size": 30}, "headline": {"max_width": 1000}}}`.
5. Report: files, font used, shortened strings, strings you translated yourself.

Many locales: one subagent per 2–3 locales (they write only their own strings file and out folder).

## Strings

```json
{"locale": "vi",
 "strings":   {"Today": "Hôm nay", "Take All": "Dùng tất cả"},
 "headlines": {"01": "Thói quen tốt\n*giữ được lâu*"}}
```
- Keys are the base-language text, so one translation serves every screenshot.
- **UI strings must match the app.** If the repo has String Catalogs, look them up:
  `$PY $S/xcstrings.py --root <repo> --locale vi "Today" "Take All"` (`--grep`, `--format KEY args`).
  Only translate what the catalog lacks, and list those for the user. No catalog (or a demo): keep
  a term list as you go so the same word is translated the same way on every screenshot.
- Times, dates and numbers as iOS shows them: `swift $S/timefmt.swift 20:00 2026-03-12 fr ko ar`
  (short time, date, weekday+day+month, month+year, grouped numbers). Grouping separators follow
  the locale (6,000 → 6 000 in French) — that's formatting, not translating.
- Headlines are marketing copy: write them natively, never word for word; keep the line count and
  roughly the length. With several screenshots, show new headlines to the user before building
  the whole set; for a single screenshot (or when the user already said go), build and show.
- `"key": "Today (tab)"` on an item lets one source string have two translations.

## Rules
- Never modify `source/`. Output keeps the exact pixel size and alpha.
- Don't translate product/brand names or units; numbers, times and dates keep their values in the
  locale's format.
- If a translation can't fit, propose shorter wording rather than shrinking far below the original.
- Example: `${CLAUDE_PLUGIN_ROOT}/examples/demo/appshots/` — a full layout (headline + 14 UI items,
  grouped) with German and French strings.
