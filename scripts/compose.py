#!/usr/bin/env python3
"""Compose App Store screenshot frames from real app captures, for every locale.

  compose.py --root appshots --locale en vi ja         build listed locales
  compose.py --root appshots --all-locales              every copy/<locale>.json
  compose.py --root appshots --locale en --only 10      some frames

Inputs under --root (see references/compose-format.md):
  brand.json                 look of the whole set (colours, headline, phone, card)
  compose/frames.json        one entry per frame: template, captures, card, copy keys
  compose/copy/<locale>.json marketing copy per locale (headline etc.)
  captures/<locale>/...      simulator captures referenced by frames.json
Output: source/<id>.png for the base locale, out/<locale>/<id>.png for the others.
"""
import argparse, glob, html, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(HERE, '..', 'templates')
RTL = {'ar', 'he', 'fa', 'ur'}

DEFAULT_BRAND = {
    "canvas": [1290, 2796],
    "base_locale": "en",
    "background": {"stops": [["#EEF2FF", 0], ["#EEF2FF", 0.62], ["#C7D2FE", 0.85], ["#A5B4FC", 1]]},
    "headline": {"color": "#1F2937", "accent": "#4F46E5", "size": 160, "top": 240,
                 "line_height": 0.95, "letter_spacing": -3, "max_width": 1180},
    "phone": {"width": 860, "top": 900, "shadow": "rgba(30, 41, 90, .28)"},
    "card": {"stroke": "#818CF8", "radius": 52, "background": "#FFFFFF"},
    "font": {"display": "SF Pro Display", "text": "SF Pro Text"},
    "decor_html": ""
}


def load(p, default=None):
    if not os.path.exists(p):
        if default is not None:
            return default
        sys.exit(f'missing {p}')
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def markup(line):
    """*accent* and ^big^ markup -> HTML spans."""
    esc = html.escape(line)
    esc = re.sub(r'\^(.+?)\^', r'<span class="big">\1</span>', esc)
    return re.sub(r'\*(.+?)\*', r'<span class="accent">\1</span>', esc)


def headline_html(text, max_width):
    lines = text.split('\n')
    return '\n'.join(f'<span class="line fit" data-maxw="{max_width}">{markup(l)}</span>' for l in lines)


def gradient(stops):
    return 'linear-gradient(to bottom, ' + ', '.join(f'{c} {round(p * 100, 2)}%' for c, p in stops) + ')'


def css_vars(brand):
    h, ph, cd = brand['headline'], brand['phone'], brand['card']
    w, H = brand['canvas']
    return '\n'.join([
        f'--canvas-w: {w}px; --canvas-h: {H}px;',
        f'--bg: {gradient(brand["background"]["stops"])};',
        f'--ink: {h["color"]}; --accent: {h["accent"]};',
        f'--headline-size: {h["size"]}px; --headline-top: {h["top"]}px;',
        f'--headline-lh: {h["line_height"]}; --headline-ls: {h["letter_spacing"]}px;',
        f'--phone-w: {ph["width"]}px; --phone-top: {ph["top"]}px; --phone-shadow: {ph["shadow"]};',
        f'--card-stroke: {cd["stroke"]}; --card-radius: {cd["radius"]}px; --card-bg: {cd["background"]};',
        f'--font-display: "{brand["font"]["display"]}", "AK Display"; --font-text: "{brand["font"]["text"]}", "AK Text";',
    ])


def font_faces():
    """SF Pro when installed, bundled Inter otherwise (same family names in the CSS)."""
    fonts = os.path.abspath(os.path.join(HERE, '..', 'fonts'))
    rules = []
    for fam, weight, sf, inter in [
            ('AK Display', 700, 'SF Pro Display Bold', 'InterDisplay-Bold.ttf'),
            ('AK Text', 400, 'SF Pro Text Regular', 'Inter-Regular.ttf'),
            ('AK Text', 500, 'SF Pro Text Medium', 'Inter-Medium.ttf'),
            ('AK Text', 600, 'SF Pro Text Semibold', 'Inter-SemiBold.ttf'),
            ('AK Text', 700, 'SF Pro Text Bold', 'Inter-Bold.ttf')]:
        rules.append(f'@font-face {{ font-family: "{fam}"; font-weight: {weight}; '
                     f'src: local("{sf}"), url("file://{fonts}/{inter}"); }}')
    return '\n'.join(rules)


def fill(template, values):
    return re.sub(r'\{\{(\w+)\}\}', lambda m: str(values.get(m.group(1), '')), template)


def resolve(root, pattern, locale, base):
    """captures/{locale}/x.png, falling back to the base locale's capture."""
    p = os.path.join(root, pattern.format(locale=locale))
    if os.path.exists(p):
        return p
    fb = os.path.join(root, pattern.format(locale=base))
    if os.path.exists(fb):
        print(f'  note: {pattern} missing for {locale}, using {base}')
        return fb
    sys.exit(f'missing capture {p}')


def build_frame(root, brand, frame, locale, copy):
    base = brand['base_locale']
    tpl_name = frame.get('template', 'phone')
    with open(os.path.join(TEMPLATES, f'{tpl_name}.html'), encoding='utf-8') as fh:
        tpl = fh.read()
    work = os.path.join(root, 'compose', 'build', locale, frame['id'])
    os.makedirs(work, exist_ok=True)
    shutil.copy(os.path.join(TEMPLATES, 'base.css'), os.path.join(work, 'base.css'))

    values = {'lang': locale, 'dir': 'rtl' if locale.split('-')[0] in RTL else 'ltr',
              'css_vars': css_vars(brand), 'font_faces': font_faces(), 'decor': brand.get('decor_html', ''),
              'title': f'{frame["id"]} {locale}'}
    for key, spec in frame.get('images', {}).items():
        # "captures/{locale}/x.png", or {"from": ..., "crop": [x0, y0, x1, y1]} for a floating card
        pattern = spec if isinstance(spec, str) else spec['from']
        src = resolve(root, pattern, locale, base)
        dst = f'{key}.png'
        crop = spec.get('crop') if isinstance(spec, dict) else None
        if isinstance(crop, dict):          # per-locale boxes: {"ja": [...], "*": [...]}
            crop = crop.get(locale, crop.get('*'))
        if crop:
            from PIL import Image
            Image.open(src).crop(tuple(crop)).save(os.path.join(work, dst))
        else:
            shutil.copy(src, os.path.join(work, dst))
        values[key] = dst
    missing = []
    for key, copy_key in frame.get('text', {}).items():
        text = copy.get(copy_key)
        if text is None:
            missing.append(copy_key)
            continue
        maxw = frame.get('max_width', {}).get(key, brand['headline']['max_width'] if key == 'headline' else 960)
        values[key] = headline_html(text, maxw) if key == 'headline' else \
            '<br>'.join(f'<span class="fit" data-maxw="{maxw}">{markup(t)}</span>' for t in text.split('\n'))
    for k, v in frame.get('style', {}).items():   # per-frame placeholder values, e.g. card_top
        values[k] = v
    # per-locale tweaks live with the copy: {"_style": {"02": {"extra_css": ".headline{line-height:1.05}"}}}
    for k, v in copy.get('_style', {}).get(frame['id'], {}).items():
        values[k] = (values.get(k, '') + '\n' + v) if k == 'extra_css' else v
    if missing:
        print(f'  UNTRANSLATED {locale}/{frame["id"]}: {missing}')
    page = os.path.join(work, 'index.html')
    with open(page, 'w', encoding='utf-8') as fh:
        fh.write(fill(tpl, values))

    out = os.path.join(root, 'source' if locale == base else os.path.join('out', locale), f'{frame["id"]}.png')
    w, h = brand['canvas']
    subprocess.run(['bash', os.path.join(HERE, 'render.sh'), page, out, str(w), str(h)], check=True,
                   stdout=subprocess.DEVNULL)
    if frame.get('onto'):
        # transparent overlay (badges, labels) composited onto an existing screenshot
        from PIL import Image
        under = Image.open(resolve(root, frame['onto'], locale, base))
        over = Image.open(out).convert('RGBA')
        res = Image.alpha_composite(under.convert('RGBA'), over)
        if under.mode != 'RGBA':
            res = res.convert(under.mode)
        res.save(out)
    return out, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--locale', nargs='*', default=[])
    ap.add_argument('--all-locales', action='store_true')
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    brand = merge(DEFAULT_BRAND, load(os.path.join(root, 'brand.json'), {}))
    frames = load(os.path.join(root, 'compose', 'frames.json'))['frames']
    if a.only:
        frames = [f for f in frames if f['id'] in a.only]
    locales = a.locale
    if a.all_locales:
        locales = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(root, 'compose', 'copy', '*.json')))
    if not locales or not frames:
        sys.exit('nothing to build: check --locale and compose/frames.json')
    problems = {}
    for loc in locales:
        copy = load(os.path.join(root, 'compose', 'copy', f'{loc}.json'), {})
        for fr in frames:
            if loc not in fr.get('locales', [loc]) or loc in fr.get('skip_locales', []):
                continue
            out, missing = build_frame(root, brand, fr, loc, copy)
            print(f'[{loc}] {fr["id"]} -> {os.path.relpath(out, root)}')
            if missing:
                problems[f'{loc}/{fr["id"]}'] = missing
    if problems:
        print('\nUNTRANSLATED COPY KEYS:')
        for k, v in problems.items():
            print(f'  {k}: {v}')


if __name__ == '__main__':
    main()
