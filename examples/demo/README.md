# Demo: "Sprout", a fictional habit tracker

- `mock/` draws the app in HTML and renders its "simulator captures" (`make_captures.py`), so this
  example runs without an Xcode project. Its UI strings are in `mock/ui.json`; a real app's come
  from its String Catalogs (`scripts/xcstrings.py`).
- `appshots/` is what the skills create in your repo:
  - compose: `brand.json`, `compose/frames.json`, `compose/copy/{en,vi,ja,ar}.json` → `source/01.png`, `out/{vi,ja,ar}/01.png`
  - localize: `layouts/01.json` + `strings/de.json` → `out/de/01.png`
- `out/` is committed here only as a showcase; in your repo, git-ignore it.

Rebuild:
```bash
PY=$(bash scripts/setup.sh | tail -1)
$PY examples/demo/mock/make_captures.py
$PY scripts/compose.py --root examples/demo/appshots --all-locales
$PY scripts/build.py --root examples/demo/appshots --locale de
```
