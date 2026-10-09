#!/usr/bin/env python3
"""Render the fictional app's 'simulator captures' for each locale (example only).

  python examples/demo/mock/make_captures.py
Writes examples/demo/appshots/captures/<locale>/today.png (1206x2622, iPhone 17 Pro).
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from compose import font_faces  # noqa: E402

UI = json.load(open(os.path.join(HERE, 'ui.json'), encoding='utf-8'))
tpl = open(os.path.join(HERE, 'app.html'), encoding='utf-8').read()
for loc, s in UI.items():
    page = os.path.join(HERE, f'_{loc}.html')
    vals = dict(s, lang=loc, dir='rtl' if loc == 'ar' else 'ltr', font_faces=font_faces())
    with open(page, 'w', encoding='utf-8') as fh:
        fh.write(re.sub(r'\{\{(\w+)\}\}', lambda m: vals.get(m.group(1), ''), tpl))
    out = os.path.join(ROOT, 'examples', 'demo', 'appshots', 'captures', loc, 'today.png')
    subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'render.sh'), page, out, '1206', '2622'], check=True)
    os.remove(page)
