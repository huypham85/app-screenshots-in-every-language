#!/usr/bin/env python3
"""Helpers for writing a layout file for a new screenshot.

  measure.py grid  src.png out.png                 # source with a labelled 100px grid (read coordinates)
  measure.py crop  src.png x0 y0 x1 y1 out.png [--scale 2]   # zoomed crop with 10px ticks
  measure.py box   src.png x0 y0 x1 y1             # ink bbox, background, text colour of a box
  measure.py pill  src.png y x                     # extents of the pill/tag containing (x,y)
  measure.py color src.png x y                     # pixel colour
  measure.py fit   src.png x0 y0 x1 y1 "Text" [role] # font size/baseline that reproduces Text in box (role default display_bold)
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shotloc

if len(sys.argv) < 3 or sys.argv[1] not in ('grid', 'crop', 'box', 'pill', 'color', 'fit'):
    sys.exit(__doc__)
cmd, src = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGB'); a = np.array(im)

if cmd == 'grid':
    g = im.copy(); d = ImageDraw.Draw(g)
    for x in range(0, im.width, 100):
        d.line([(x, 0), (x, im.height)], fill=(255, 0, 0) if x % 500 == 0 else (255, 120, 120), width=2 if x % 500 == 0 else 1)
        d.text((x+3, 3), str(x), fill=(255, 0, 0))
    for y in range(0, im.height, 100):
        d.line([(0, y), (im.width, y)], fill=(255, 0, 0) if y % 500 == 0 else (255, 120, 120), width=2 if y % 500 == 0 else 1)
        d.text((3, y+3), str(y), fill=(255, 0, 0))
    g.save(sys.argv[3]); print('saved', sys.argv[3])
elif cmd == 'crop':
    x0, y0, x1, y1 = map(int, sys.argv[3:7]); out = sys.argv[7]
    s = int(sys.argv[sys.argv.index('--scale')+1]) if '--scale' in sys.argv else 2
    c = im.crop((x0, y0, x1, y1)).resize(((x1-x0)*s, (y1-y0)*s), Image.NEAREST); d = ImageDraw.Draw(c)
    for x in range((x0//10+1)*10, x1, 10):
        L = 14 if x % 50 == 0 else 6; d.line([((x-x0)*s, 0), ((x-x0)*s, L)], fill=(255, 0, 0))
        if x % 50 == 0: d.text(((x-x0)*s+2, L), str(x), fill=(255, 0, 0))
    for y in range((y0//10+1)*10, y1, 10):
        L = 14 if y % 50 == 0 else 6; d.line([(0, (y-y0)*s), (L, (y-y0)*s)], fill=(255, 0, 0))
        if y % 50 == 0: d.text((L+2, (y-y0)*s), str(y), fill=(255, 0, 0))
    c.save(out); print('saved', out)
elif cmd == 'box':
    box = list(map(int, sys.argv[3:7]))
    bb, bg, col = shotloc.measure(a, box)
    touch = [n for n, v, w in [('left', bb[0], box[0]), ('top', bb[1], box[1]), ('right', bb[2], box[2]), ('bottom', bb[3], box[3])] if abs(v-w) <= 1]
    print(f'ink={bb} bg={tuple(int(v) for v in bg)} color={col}' + (f'  WARNING ink touches box {touch}: box may cut text or include a neighbour' if touch else ''))
elif cmd == 'pill':
    y, x = int(sys.argv[3]), int(sys.argv[4]); A = a.astype(int)
    out = lambda p: p.min() > 247 or (abs(p[0]-p[1]) < 5 and abs(p[1]-p[2]) < 7)
    l = x
    while not out(A[y, l-1]): l -= 1
    r = x
    while not out(A[y, r+1]): r += 1
    cx = l+25; t = y
    while not out(A[t-1, cx]): t -= 1
    b = y
    while not out(A[b+1, cx]): b += 1
    print(f'pill=[{l},{t},{r},{b+1}] color={tuple(A[y, (l+r)//2])}')
elif cmd == 'color':
    x, y = int(sys.argv[3]), int(sys.argv[4]); print(tuple(int(v) for v in a[y, x]))
elif cmd == 'fit':
    box = list(map(int, sys.argv[3:7])); text = sys.argv[7]; role = sys.argv[8] if len(sys.argv) > 8 else 'display_bold'
    bb, bg, col = shotloc.measure(a, box, 60 if role == 'display_bold' else 38)
    f, base, left, w = shotloc.fit_font(role, text, bb)
    print(f'ink={bb} size={f.size} base={base:.0f} color={col} font={shotloc.FONT_NAME}')
