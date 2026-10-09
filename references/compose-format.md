# Compose files (`appshots/brand.json`, `appshots/compose/`)

## brand.json — the look of the whole set

```json
{
  "canvas": [1290, 2796],
  "base_locale": "en",
  "background": {"stops": [["#EEF2FF", 0], ["#EEF2FF", 0.6], ["#C7D2FE", 0.84], ["#A5B4FC", 1]]},
  "headline": {"color": "#1F2937", "accent": "#4F46E5", "size": 160, "top": 230,
               "line_height": 0.95, "letter_spacing": -3, "max_width": 1180},
  "phone": {"width": 860, "top": 640, "shadow": "rgba(30, 41, 90, .28)"},
  "card": {"stroke": "#818CF8", "radius": 48, "background": "#FFFFFF"},
  "font": {"display": "SF Pro Display", "text": "SF Pro Text"},
  "decor_html": ""
}
```

| key | meaning |
|---|---|
| `canvas` | output size; 1290×2796 is the required 6.9" iPhone set |
| `base_locale` | its frames are written to `source/`, the others to `out/<locale>/` |
| `background.stops` | vertical gradient `[colour, 0..1]`; one stop = flat colour |
| `headline` | colours, size/top in px; `max_width`: lines wider than this shrink (long languages) |
| `phone` | width and top of the CSS-drawn device; shadow colour |
| `card` | floating card stroke, radius, background |
| `font` | families tried first; SF Pro if installed, bundled Inter otherwise |
| `decor_html` | raw HTML added to every frame (blurred shapes, a faint line…) — keep it subtle |

Unspecified keys fall back to the defaults in `scripts/compose.py`. `learn_brand.py` writes a
starting `brand.json` from existing screenshots.

## compose/frames.json — one entry per frame

```json
{"frames": [
  {"id": "02", "template": "phone-card",
   "images": {"screen": "captures/{locale}/today.png",
              "card": {"from": "captures/{locale}/today.png",
                       "crop": {"*": [48, 510, 1158, 800], "ja": [48, 530, 1158, 820]}}},
   "text": {"headline": "headline.02"},
   "style": {"card_top": "2290px", "card_width": "1110px"},
   "skip_locales": ["hi"]},
  {"id": "01", "template": "overlay-badges", "onto": "source/_base/01.png",
   "images": {"laurel_l": "assets/laurel_l.png", "laurel_r": "assets/laurel_r.png"},
   "text": {"badge_left": "badge.reviews", "badge_right": "badge.loved"},
   "style": {"badges_top": "58px"}}
]}
```

| key | meaning |
|---|---|
| `id` | output file name (`source/<id>.png`) |
| `template` | `phone`, `phone-card`, `overlay-badges` (files in `templates/`), or your own HTML there |
| `images` | `{placeholder: path}`; `{locale}` is replaced, falling back to the base locale's file. `{"from", "crop": [x0,y0,x1,y1]}` cuts a region; `crop` may also be `{"ja": [...], "*": [...]}` per locale |
| `text` | `{placeholder: copy key}` looked up in `copy/<locale>.json` |
| `style` | raw values for template placeholders such as `card_top` |
| `max_width` | `{placeholder: px}` for text boxes that must shrink to fit |
| `onto` | composite this (transparent) frame onto an existing PNG — never onto its own output |
| `locales` / `skip_locales` | build only for / skip these locales (feature not available there) |
| `style.extra_css` | CSS for this frame only, e.g. `"style": {"extra_css": ".phone { top: 900px; }"}` |

## compose/copy/<locale>.json — marketing copy

```json
{"headline.02": "Build habits\nthat *stick*", "badge.reviews": "5-star reviews", "badge.loved": "Loved by\nthousands"}
```
Per-locale tweaks go here too: `"_style": {"02": {"extra_css": ".headline { line-height: 1.08; }"}}`.

`\n` breaks lines, `*word*` uses the accent colour, `^word^` is 1.25× larger. Copy is marketing:
write it natively per language, never word for word. UI text inside the phone comes from the
capture itself, already localized by the app.
