#!/usr/bin/env python3
"""Visual QA.

  compare.py side   original.png built.png out.png         # side-by-side (half size)
  compare.py sheet  <screens dir> <locale> out.png         # contact sheet: source row + locale row
  compare.py diff   original.png roundtrip.png             # % identical pixels + worst regions
  compare.py set    <screens dir> out.png [locale ...]     # every source/*.png in a row, plus one row
                                                           # per locale from out/<locale>/ (compose QA)
  compare.py preview in.png out.png [scale]                # scaled preview (default 0.5)
  compare.py halves in.png out.png                         # out_0.png / out_1.png: halves at 60 %
"""
import sys, os, glob
import numpy as np
from PIL import Image

if len(sys.argv) < 3:
    sys.exit(__doc__)
cmd = sys.argv[1]
if cmd == 'side':
    a = Image.open(sys.argv[2]).convert('RGB'); b = Image.open(sys.argv[3]).convert('RGB')
    s = Image.new('RGB', (a.width*2+20, a.height), 'white'); s.paste(a, (0, 0)); s.paste(b, (a.width+20, 0))
    s.resize((s.width//2, s.height//2)).save(sys.argv[4]); print('saved', sys.argv[4])
elif cmd == 'sheet':
    root, loc, out = sys.argv[2], sys.argv[3], sys.argv[4]
    import json
    lays = sorted(glob.glob(os.path.join(root, 'layouts', '*.json')))
    srcs = [Image.open(os.path.normpath(os.path.join(os.path.dirname(p), json.load(open(p))['source']))).convert('RGB') for p in lays]
    outs = [Image.open(os.path.join(root, 'out', loc, os.path.basename(p)[:-5]+'.png')).convert('RGB') for p in lays]
    w, h = 430, int(430*srcs[0].height/srcs[0].width)
    sheet = Image.new('RGB', (len(lays)*(w+16), 2*h+16), 'white')
    for i, (s, o) in enumerate(zip(srcs, outs)):
        sheet.paste(s.resize((w, h)), (i*(w+16), 0)); sheet.paste(o.resize((w, h)), (i*(w+16), h+16))
    sheet.save(out); print('saved', out)
elif cmd == 'set':
    root, out, locs = sys.argv[2], sys.argv[3], sys.argv[4:]
    ids = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(root, 'source', '*.png')))
    rows = [os.path.join(root, 'source')] + [os.path.join(root, 'out', l) for l in locs]
    w = 300; h = None; tiles = []
    for r in rows:
        row = []
        for i in ids:
            p = os.path.join(r, i + '.png')
            row.append(Image.open(p).convert('RGB') if os.path.exists(p) else None)
        tiles.append(row)
    first = next(t for row in tiles for t in row if t)
    h = int(w * first.height / first.width)
    sheet = Image.new('RGB', (len(ids) * (w + 12), len(rows) * (h + 12)), 'white')
    for ri, row in enumerate(tiles):
        for ci, t in enumerate(row):
            if t:
                sheet.paste(t.resize((w, h)), (ci * (w + 12), ri * (h + 12)))
    sheet.save(out); print('saved', out, 'frames:', ' '.join(ids))
elif cmd == 'preview':
    im = Image.open(sys.argv[2]).convert('RGB'); k = float(sys.argv[4]) if len(sys.argv) > 4 else .5
    im.resize((int(im.width * k), int(im.height * k))).save(sys.argv[3]); print('saved', sys.argv[3])
elif cmd == 'halves':
    # top and bottom half at 60 % — the size to read small UI text at during QA
    im = Image.open(sys.argv[2]).convert('RGB'); base = os.path.splitext(sys.argv[3])[0]
    for i, (y0, y1) in enumerate([(0, im.height // 2 + 80), (im.height // 2 - 80, im.height)]):
        c = im.crop((0, y0, im.width, y1)); c = c.resize((int(c.width * .6), int(c.height * .6)))
        c.save(f'{base}_{i}.png'); print('saved', f'{base}_{i}.png')
elif cmd == 'diff':
    a = np.array(Image.open(sys.argv[2]).convert('RGB')).astype(int)
    b = np.array(Image.open(sys.argv[3]).convert('RGB')).astype(int)
    if a.shape != b.shape:
        sys.exit(f'SIZE MISMATCH {a.shape} vs {b.shape}')
    d = np.abs(a-b).sum(2)
    print(f'identical (<=6): {100*(d <= 6).mean():.2f}%')
    H, W = d.shape; cells = []
    for y in range(0, H, 100):
        for x in range(0, W, 100):
            cells.append((d[y:y+100, x:x+100].mean(), x, y))
    for v, x, y in sorted(cells, reverse=True)[:8]:
        print(f'  region x={x}-{x+100} y={y}-{y+100}: mean diff {v:.1f}')
