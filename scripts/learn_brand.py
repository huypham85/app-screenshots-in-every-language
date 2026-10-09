#!/usr/bin/env python3
"""Suggest a brand.json by measuring an app's existing App Store screenshots.

  learn_brand.py <screenshot.png> [more.png ...] [--out appshots/brand.json]

Measures, per image, then takes the median:
  - background: colour of the left/right edge columns down the image -> gradient stops
  - headline: ink in the top 22% that differs from the background, split into two colour
    clusters (dark ink + accent), first ink row (top) and the first line's ink height (size)
  - phone: width of the dark device frame on a row through the middle
These are suggestions: always look at the result next to the originals and adjust.
"""
import argparse, json, sys

import cv2
import numpy as np
from PIL import Image


def hexc(rgb):
    return '#%02X%02X%02X' % tuple(int(round(v)) for v in rgb)


def background(a):
    H = a.shape[0]
    edge = np.concatenate([a[:, 4:24], a[:, -24:-4]], axis=1).astype(float)
    rows = np.median(edge, axis=1)                     # one colour per row
    stops = []
    for f in (0, .25, .5, .62, .75, .85, .95, 1):
        y = min(H - 1, int(f * (H - 1)))
        stops.append((hexc(rows[max(0, y - 6):y + 6].mean(0)), round(f, 2)))
    # drop stops that repeat the previous colour
    out = [stops[0]]
    for c, f in stops[1:]:
        if c != out[-1][0] or f == 1:
            out.append((c, f))
    return out, rows


def headline(a, rows):
    H, W = a.shape[:2]
    # central columns only: decorations (blurred pills, icons) sit near the corners
    x0, x1 = int(W * .12), int(W * .88)
    top = a[:int(H * .22), x0:x1].astype(float)
    bg = rows[:int(H * .22)][:, None, :]
    diff = np.abs(top - bg).sum(2)
    ink = diff > 150                                   # glyph cores, not soft decor
    ys, xs = np.where(ink)
    if len(ys) < 500:
        return None
    px = top[ink].astype(np.float32)
    _, labels, centers = cv2.kmeans(px, 3, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, .5),
                                    4, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(labels.ravel(), minlength=3) / len(labels)
    lum = centers @ np.array([.299, .587, .114])
    sat = centers.max(1) - centers.min(1)
    big = [i for i in range(3) if share[i] > .12]       # ignore small clusters (photos, anti-aliasing)
    dark = centers[min(big, key=lambda i: lum[i])]
    colourful = [i for i in big if sat[i] > 40 and lum[i] < 200]
    accent = centers[max(colourful, key=lambda i: sat[i] * share[i])] if colourful else dark
    # first text line: first band of rows with ink
    rowink = ink.sum(1) > (x1 - x0) * .01
    first = int(np.argmax(rowink))
    end = first
    while end < len(rowink) and rowink[end]:
        end += 1
    size = round((end - first) / 0.8)                  # first line ink band ~0.8 em (calibrated on SF Pro Display Bold)
    return {"color": hexc(dark), "accent": hexc(accent), "top": max(0, first - round(size * .2)),
            "size": size}


def phone(a):
    H, W = a.shape[:2]
    y = int(H * .55)
    lum = a[y].astype(float) @ np.array([.299, .587, .114])
    dark = np.where(lum < 60)[0]
    if len(dark) < 2:
        return None
    left, right = int(dark.min()), int(dark.max())
    if right - left < W * .4:
        return None
    return {"width": right - left}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('images', nargs='+')
    ap.add_argument('--out')
    a = ap.parse_args()
    bgs, heads, phones, size = [], [], [], None
    for p in a.images:
        im = np.array(Image.open(p).convert('RGB'))
        size = size or [im.shape[1], im.shape[0]]
        stops, rows = background(im)
        bgs.append(stops)
        h = headline(im, rows)
        if h:
            heads.append(h)
        ph = phone(im)
        if ph:
            phones.append(ph)
    brand = {"canvas": size, "background": {"stops": bgs[0]}}
    if heads:
        med = lambda k: int(np.median([h[k] for h in heads]))
        # per-channel median across images: one odd frame (a photo above the text) can't win
        mcol = lambda k: hexc(np.median([[int(h[k][i:i + 2], 16) for i in (1, 3, 5)] for h in heads], axis=0))
        brand["headline"] = {"color": mcol("color"), "accent": mcol("accent"),
                             "size": med("size"), "top": med("top")}
    if phones:
        brand["phone"] = {"width": int(np.median([p["width"] for p in phones]))}
    text = json.dumps(brand, indent=2)
    if a.out:
        with open(a.out, 'w') as fh:
            fh.write(text + '\n')
    print(text)
    print(f'\nmeasured {len(a.images)} image(s): headline in {len(heads)}, phone in {len(phones)}',
          file=sys.stderr)


if __name__ == '__main__':
    main()
