#!/usr/bin/env python3
"""Build localized screenshots.

  build.py --root <screens dir> --locale vi                 # all layouts for one locale
  build.py --root <screens dir> --locale vi --only 01 03    # some screenshots
  build.py --root <screens dir> --all-locales               # every strings/*.json
  build.py --root <screens dir> --locale en --roundtrip     # re-render source text (verification)

<screens dir> contains: layouts/<NN>.json, strings/<locale>.json; output -> out/<locale>/<NN>.png
"""
import argparse, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shotloc

ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True)
ap.add_argument('--locale', nargs='*', default=[])
ap.add_argument('--all-locales', action='store_true')
ap.add_argument('--only', nargs='*')
ap.add_argument('--roundtrip', action='store_true', help='render source strings (no translation) to verify layout')
ap.add_argument('--out', default=None)
a = ap.parse_args()

root = os.path.abspath(a.root)
layouts = sorted(glob.glob(os.path.join(root, 'layouts', '*.json')))
if a.only:
    layouts = [p for p in layouts if os.path.splitext(os.path.basename(p))[0] in a.only]
locales = a.locale
if a.all_locales:
    locales = sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(root, 'strings', '*.json')))
if a.roundtrip:
    locales = ['_roundtrip']
if not layouts or not locales:
    sys.exit('nothing to build: check --root/layouts and --locale')
problems = {}
for loc in locales:
    sp = None if loc == '_roundtrip' else os.path.join(root, 'strings', f'{loc}.json')
    if sp and not os.path.exists(sp):
        sys.exit(f'missing strings file {sp}')
    for lp in layouts:
        nn = os.path.splitext(os.path.basename(lp))[0]
        out = os.path.join(a.out or os.path.join(root, 'out'), loc, f'{nn}.png')
        print(f'[{loc}] {nn}')
        _, missing = shotloc.build(lp, sp, out)
        if missing and loc != '_roundtrip':
            problems[f'{loc}/{nn}'] = missing
if problems:
    print('\nUNTRANSLATED KEYS (source text was kept):')
    for k, v in problems.items():
        print(f'  {k}: {v}')
