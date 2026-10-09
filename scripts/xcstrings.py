#!/usr/bin/env python3
"""Look up an app's own translations in its Xcode String Catalogs (*.xcstrings).

  xcstrings.py --root <app repo> --locale vi "Today" "Take All" ...   exact key lookup
  xcstrings.py --root <app repo> --locale vi --grep "before %"       keys containing text
  xcstrings.py --root <app repo> --locales                           locales present
  xcstrings.py --root <app repo> --locale de --format "%lld min before %@" 30 Breakfast

Exact key match (case-sensitive) wins over case-insensitive and English-value matches.
Plural/device variations are printed as JSON so you can pick the right form.
"""
import argparse, glob, json, os, re, sys

SKIP = ('/.build/', '/DerivedData/', '/Pods/', '/.claude/', '/node_modules/')


def catalogs(root):
    for p in glob.glob(os.path.join(root, '**', '*.xcstrings'), recursive=True):
        if not any(s in p for s in SKIP):
            yield p


def load(root):
    rows = []
    for p in sorted(catalogs(root)):
        with open(p, encoding='utf-8') as fh:
            d = json.load(fh)
        for key, v in d.get('strings', {}).items():
            rows.append((key, v.get('localizations', {}), os.path.relpath(p, root)))
    return rows


def value(locs, locale):
    u = locs.get(locale)
    if not u:
        return None
    if 'stringUnit' in u:
        return u['stringUnit'].get('value')
    return json.dumps(u, ensure_ascii=False)


def fill(fmt, args):
    """Apple format string with %@ / %lld / %d, positional (%1$@) or not."""
    def pos(m):
        return str(args[int(m.group(1)) - 1])
    out = re.sub(r'%(\d+)\$(?:@|lld|ld|d)', pos, fmt)
    it = iter(args)
    return re.sub(r'%(?:@|lld|ld|d)', lambda m: str(next(it)), out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--locale')
    ap.add_argument('--grep')
    ap.add_argument('--locales', action='store_true')
    ap.add_argument('--format', nargs='+', metavar=('KEY', 'ARG'))
    ap.add_argument('keys', nargs='*')
    a = ap.parse_args()
    rows = load(a.root)
    if not rows:
        sys.exit(f'no .xcstrings under {a.root}')
    if a.locales:
        found = sorted({l for _, locs, _ in rows for l in locs})
        print(' '.join(found))
        return
    if a.grep:
        q = a.grep.lower()
        for key, locs, f in rows:
            if q in key.lower():
                print(f'{key!r} => {value(locs, a.locale)!r}  [{f}]')
        return
    if a.format:
        key, *args = a.format
        hit = next((value(l, a.locale) for k, l, _ in rows if k == key and value(l, a.locale)), None)
        if hit is None:
            sys.exit(f'no {a.locale} value for {key!r}')
        print(fill(hit, args))
        return
    for q in a.keys:
        hits = [r for r in rows if r[0] == q] + [r for r in rows if r[0] != q and r[0].lower() == q.lower()]
        hits += [r for r in rows if r not in hits and (value(r[1], 'en') or '').lower() == q.lower()]
        hits = [h for h in hits if value(h[1], a.locale)]
        if hits:
            print(f'{q!r} => ' + '; '.join(f'{value(l, a.locale)!r} [{k!r}, {f}]' for k, l, f in hits[:3]))
        else:
            print(f'{q!r} => NONE (translate yourself and tell the user)')


if __name__ == '__main__':
    main()
