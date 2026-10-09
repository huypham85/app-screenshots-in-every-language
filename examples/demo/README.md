# Demo: "Sprout", a fictional habit tracker

- `mock/` draws the app in HTML and renders its "simulator captures" (`make_captures.py`), so this
  example runs without an Xcode project. Its UI strings are in `mock/ui.json`; a real app's come
  from its String Catalogs (`scripts/xcstrings.py`).
- `appshots/` is what the skills create in your repo:
  - compose: `brand.json`, `compose/frames.json`, `compose/copy/{en,vi,ja,ar}.json` → `source/01–03.png`, `out/{vi,ja,ar}/01–03.png`
  - localize: `layouts/01.json` + `strings/{de,fr}.json` → `out/{de,fr}/01.png`
- `hero/hero.html` renders the README banner (`docs/hero.jpg`) with `scripts/render.sh … 2400 1350`.
- `out/` is committed here only as a showcase; in your repo, git-ignore it.

Rebuild:
```bash
PY=$(bash scripts/setup.sh | tail -1)
$PY examples/demo/mock/make_captures.py
$PY scripts/compose.py --root examples/demo/appshots --all-locales
$PY scripts/build.py --root examples/demo/appshots --locale de fr
```
