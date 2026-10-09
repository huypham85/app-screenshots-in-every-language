# Layout file format (`layouts/NN.json`)

All coordinates are source-image pixels `[x0, y0, x1, y1]` (x1/y1 exclusive).
A working file: `examples/demo/appshots/layouts/01.json`. Coordinates below are illustrative.

```json
{
  "source": "../source/01.png",
  "headline": {
    "key": "01",
    "src_lines": ["Today’s dose", "at a *glance*"],
    "line_boxes": [[130,285,1130,447], [130,440,1130,600]],
    "erase": [110,270,1190,610],
    "colors": {"dark": [41,42,42], "accent": [0,119,107]},
    "font": "display_bold",
    "max_width": 1070,
    "cx": 631
  },
  "groups": {
    "weekdays": {"share_size": true},
    "tabs": {"share_size": true, "share_base": true}
  },
  "items": [
    {"src": "Today", "weight": "bold", "box": [225,965,440,1055]},
    {"src": "WED", "weight": "med", "box": [245,1108,321,1142], "align": "center", "group": "weekdays"},
    {"src": "30 min before lunch", "weight": "semi", "box": [566,2126,902,2166], "pill": [508,2117,918,2179]},
    {"src": "Add", "weight": "semi", "box": [930,2358,1012,2402],
     "button": {"x0": 850, "x1": 1038, "icon": [888,2362,922,2396], "fill": [3,142,126]}},
    {"src": "Today", "weight": "semi", "box": [310,2540,390,2576], "align": "center", "cx": 349, "group": "tabs"}
  ]
}
```

## Items

| key | meaning |
|---|---|
| `src` | English text exactly as in the image; also the lookup key in `strings` (unless `key` is set) |
| `weight` | `reg` `med` `semi` `bold` (iOS UI weights, SF Pro Text); `display_bold` for large display text (page titles, callout titles, a headline line that sits on a pill) |
| `box` | encloses the string's ink + a little of its own background. Its border pixels define the background colour, so it must not cross icons, tag edges or other text |
| `align` | `left` (default: keeps the original left edge), `center`, or `right` (keeps the original right edge, e.g. iOS notification timestamps, values before a chevron) |
| `cx` | centre x for `center` (default: centre of the original ink). Use the icon centre for tab labels |
| `rx` | right edge for `right` (default: right of the original ink) |
| `pill` | tag behind the text: `[x0,y0,x1,y1]` of the tag; it is stretched/shrunk so the new text keeps the original right padding (left edge fixed) |
| `pill_anchor` | `"right"`: the pill's right edge stays fixed and it grows/shrinks to the left; the text keeps its right padding. Use for pills at the right end of a card or banner (Refill, Taken) and for headline pills that line up on the right |
| `push` | `[x0,y0,x1,y1]`: when this item's text gets wider, everything in this region moves right by the same amount (content past x1 is dropped, the gap is filled with column x0). Use for chip rows ("All" → "Tất cả" pushes the next chips) and for "Pill • ⚠ 1 left" style rows. x0 must be a clean background column just right of the item. Later items whose box starts inside the region move along automatically |
| `button` | `{x0,x1}` of a button + `icon` rect + flat `fill` colour: icon and label are re-centred together |
| `group` | items sharing size (and baseline if the group has `share_base`) |
| `size` | force a font size (px). Use when a width-only fit looks too short or too tall, or to shrink one translation that would overflow its card |
| `base` / `dx` / `x` | force baseline y / nudge x / set the ink-left x explicitly. Last resort, or for text whose original ink is partly hidden |
| `color` | force text colour `[r,g,b]` (default: measured) |
| `thresh` | ink-detection threshold (default 38); lower for faint text on tinted glass |
| `key` | strings key when the same English text needs different translations (e.g. `"Start Date (stat card)"` for a narrow card, `"(phone) Lunch"` for a cut-off fragment) |
| `erase` | how the old text is removed: default = flat refill from the box border; `"fit"` = low-order surface fit (text on a glow, a dimmed overlay or any soft gradient; leaves no flat patch); `"vfill"` = each column interpolated between the clean rows above and below the ink (background that changes left to right, e.g. content fading into a card's glow) |
| `fit_box` / `fit_deg` | for `"fit"`: a larger rect to fit the surface over (so it sees where a glow is heading), and the polynomial degree (default 2) |
| `erase_rect` | for `"vfill"`: the rect to refill; needs clean background rows at its top and bottom |
| `clip` / `fade` | draw the translation only inside `clip` `[x0,y0,x1,y1]`, fading to transparent over the last `fade` px. For text that runs under an overlay (a zoomed card on top of the phone): give the visible fragment as `src`, a `key` for the full translation, explicit `size`/`base`/`x`, `erase: "vfill"` |

Size is fitted from the original ink (width-first, so a different font occupies the same space);
baseline from the original ink bottom. Strings with descenders still work because the English
`src` is rendered the same way for the fit.

## Headline

- Text on the gradient is erased by a smooth surface fit over `erase` (one box or a list of boxes;
  each must contain only background + headline: keep swooshes, pills, icons and phone frames out).
- Each `line_box` covers one line; boxes may overlap (tight headlines share rows between one line's
  descenders and the next line's ascenders). Size comes from line width, baselines from the row
  profile, centre from the ink.
- `colors.dark` / `colors.accent`: sample with `measure.py color`. Accent words are `*…*` in both
  `src_lines` and translations.
- `^…^` marks a BIG segment (one word visibly larger than the rest of its line, e.g. "Track your");
  its size is `big_size`. Markers nest: `^*Track*^ your`. Translations may use them too.
- Optional: `sizes` (base size per line, when lines differ, e.g. small "Prescriptions" over large
  "Under control"; measure with `measure.py fit` on one word), `per_line_size: true` (keep each
  line's measured size), `cxs` (centre x per line), `bases` (baseline y per line when the row
  profile is fooled, e.g. by a background line through the text), `ink_sum` (ink threshold for the
  erase; lower it when the gradient itself is dark, e.g. 420).
- A headline line drawn on a coloured pill is NOT part of the headline: make it an item
  (`display_bold`, box inside the pill, `pill`, usually `pill_anchor: "right"`).
- `max_width` (default image width − 220): wider translations are scaled down to fit.
- Translations with diacritics get extra line spacing only if they would otherwise touch the line above.

## Per-locale overrides (in `strings/<locale>.json`, not in the layout)

```json
"layout_overrides": {
  "09": {"Refill": {"size": 46}, "Start Date (stat card)": {"size": 22}},
  "07": {"headline": {"big_size": 200}}
}
```
Keys are item keys (`key`, else `src`); every item matching it gets the options merged in. The key
`headline` merges into the headline options. Use this for fixes that only one language needs.
