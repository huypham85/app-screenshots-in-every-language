"""shotloc — text-only localization of App Store screenshots (PNG in, PNG out).

Pipeline per screenshot:
  1. measure every text item on the pristine source (ink bbox, colour, font size, baseline)
  2. erase the text (ink mask + AA halo, refilled from surrounding background)
  3. resize pills/tags so they hug the new text with the ORIGINAL padding
  4. redraw translated text at the same baseline/alignment/colour/weight
  5. headline: erase on gradient via smooth surface fit, redraw with accent words

Part of appshotkit (MIT). Layout (per screenshot, locale-independent) and strings (per locale, shared by all
screenshots) are JSON — see references/layout-format.md.

Beyond the basics, items support: right alignment, right-anchored pills, pushing the
neighbours to the right when text grows, explicit x, background-aware erasing (surface fit,
per-column interpolation) and clipped/fading text under overlays. Headlines support per-line
sizes and centres, ^big^ word segments and several erase boxes.
"""
import functools, json, os, re
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SS = 4  # supersampling for text rendering

# ---------------------------------------------------------------- fonts
def _sf(name):
    """SF Pro from developer.apple.com/fonts, installed system-wide or per user."""
    return [os.path.join(d, name) for d in ('/Library/Fonts', os.path.expanduser('~/Library/Fonts'))]


SF_CANDIDATES = {
    'reg': _sf('SF-Pro-Text-Regular.otf'),
    'med': _sf('SF-Pro-Text-Medium.otf'),
    'semi': _sf('SF-Pro-Text-Semibold.otf'),
    'bold': _sf('SF-Pro-Text-Bold.otf'),
    'display_bold': _sf('SF-Pro-Display-Bold.otf'),
}
INTER = {k: os.path.join(HERE, '..', 'fonts', v) for k, v in {
    'reg': 'Inter-Regular.ttf', 'med': 'Inter-Medium.ttf', 'semi': 'Inter-SemiBold.ttf',
    'bold': 'Inter-Bold.ttf', 'display_bold': 'InterDisplay-Bold.ttf'}.items()}


def resolve_fonts(prefer=None):
    """SF Pro if every weight is installed (exact iOS look), else bundled Inter."""
    prefer = prefer or os.environ.get('SHOTLOC_FONTS', 'auto')
    sf = {k: next((p for p in v if os.path.exists(p)), None) for k, v in SF_CANDIDATES.items()}
    if prefer in ('auto', 'sf') and all(sf.values()):
        return 'SF Pro', sf
    if prefer == 'sf':
        missing = [k for k, v in sf.items() if not v]
        raise SystemExit(f'SF Pro not installed for: {missing}. Install from developer.apple.com/fonts')
    return 'Inter', INTER


FONT_NAME, FONTS = resolve_fonts()


# Scripts SF Pro does not cover: the locale's iOS system font draws those characters, SF Pro
# keeps drawing Latin letters and digits (drug names, times), like iOS does.
_HIRA = '/System/Library/Fonts/ヒラギノ角ゴシック W%d.ttc'
_SFAR, _SFIN = '/System/Library/Fonts/SFArabic.ttf', '/System/Library/Fonts/SFIndia.ttc'
_SDGN, _HGB = '/System/Library/Fonts/AppleSDGothicNeo.ttc', '/System/Library/Fonts/Hiragino Sans GB.ttc'
SCRIPT_FONTS = {  # role -> (path, ttc index, variable-font weight name)
    'ja': {'reg': (_HIRA % 3, 0, None), 'med': (_HIRA % 4, 0, None), 'semi': (_HIRA % 6, 0, None),
           'bold': (_HIRA % 6, 0, None), 'display_bold': (_HIRA % 7, 0, None)},
    'ko': {'reg': (_SDGN, 0, None), 'med': (_SDGN, 2, None), 'semi': (_SDGN, 4, None),
           'bold': (_SDGN, 6, None), 'display_bold': (_SDGN, 6, None)},
    # PingFang ships in a format FreeType cannot read; Hiragino Sans GB is the closest readable face
    'zh': {'reg': (_HGB, 0, None), 'med': (_HGB, 0, None), 'semi': (_HGB, 2, None),
           'bold': (_HGB, 2, None), 'display_bold': (_HGB, 2, None)},
    'ar': {'reg': (_SFAR, 0, 'Regular'), 'med': (_SFAR, 0, 'Medium'), 'semi': (_SFAR, 0, 'Semibold'),
           'bold': (_SFAR, 0, 'Bold'), 'display_bold': (_SFAR, 0, 'Bold')},
    'hi': {'reg': (_SFIN, 1, 'Regular'), 'med': (_SFIN, 1, 'Medium'), 'semi': (_SFIN, 1, 'Semibold'),
           'bold': (_SFIN, 1, 'Bold'), 'display_bold': (_SFIN, 1, 'Bold')},
}
_SCRIPT_RANGES = [(0x0590, 0x08FF), (0x0900, 0x097F), (0xA8E0, 0xA8FF), (0x1100, 0x11FF),
                  (0x2E80, 0x2FDF), (0x3000, 0x303F), (0x3040, 0x30FF), (0x3100, 0x318F),
                  (0x31F0, 0x31FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xA960, 0xA97F),
                  (0xAC00, 0xD7AF), (0xF900, 0xFAFF), (0xFB1D, 0xFDFF), (0xFE30, 0xFE4F),
                  (0xFE70, 0xFEFF), (0xFF00, 0xFFEF)]
_NEUTRAL = set(' \u00a0\u202f•·,.:;!?()[]-–—/+×"\'')
LANG = None  # set per build from strings['locale']


def set_locale(locale):
    global LANG
    lang = (locale or '').split('-')[0].split('_')[0]
    LANG = lang if lang in SCRIPT_FONTS else None


@functools.lru_cache(maxsize=None)
def _pil(spec, size, raqm):
    path, index, var = spec
    f = ImageFont.truetype(path, size, index=index,
                           layout_engine=ImageFont.Layout.RAQM if raqm else ImageFont.Layout.BASIC)
    if var:
        f.set_variation_by_name(var)
    return f


@functools.lru_cache(maxsize=None)
def _cmap(path, index):
    """Code points a font can draw (script fonts often lack • – ( ) ? %)."""
    from fontTools.ttLib import TTFont
    return frozenset(TTFont(path, fontNumber=index, lazy=True).getBestCmap())


def _is_script(ch):
    o = ord(ch)
    return any(a <= o <= b for a, b in _SCRIPT_RANGES)


class Font:
    """SF Pro (or Inter) for Latin; the locale's script font for CJK/Arabic/Devanagari runs.
    Same getbbox/getlength/size surface as a PIL font. Arabic runs are laid out right-to-left."""

    def __init__(self, role, size):
        self.role, self.size = role, int(size)
        self.latin = _pil((FONTS[role], 0, None), self.size, False)
        self.script = _pil(SCRIPT_FONTS[LANG][role], self.size, True) if LANG else None
        self.script_cmap = _cmap(*SCRIPT_FONTS[LANG][role][:2]) if LANG else None
        self.rtl = LANG == 'ar'

    def scaled(self, k):
        return Font(self.role, self.size*k)

    def runs(self, text):
        """[(segment, pil font, direction)] in visual order."""
        if not self.script:
            return [(text, self.latin, None)]
        cls = ['N' if c in _NEUTRAL else ('S' if _is_script(c) else 'L') for c in text]
        if self.rtl:  # trailing punctuation follows the paragraph direction
            i = len(cls)-1
            while i >= 0 and cls[i] == 'N':
                cls[i] = 'S'; i -= 1
        # neutrals (spaces, punctuation) take the class of the strong characters around them;
        # between two different classes they follow the paragraph: script for RTL, else the left one
        strong = [i for i, c in enumerate(cls) if c != 'N']
        for i, c in enumerate(cls):
            if c != 'N':
                continue
            prev = next((cls[j] for j in reversed(strong) if j < i), None)
            nxt = next((cls[j] for j in strong if j > i), None)
            if prev and nxt and prev != nxt:
                cls[i] = 'S' if self.rtl else prev
            else:
                cls[i] = prev or nxt or 'S'
        runs = []
        for ch, c in zip(text, cls):
            if runs and runs[-1][0] == c:
                runs[-1][1] += ch
            else:
                runs.append([c, ch])
        out = []
        for c, t in runs:
            if c != 'S':
                out.append((t, self.latin, None)); continue
            # characters the script font lacks (punctuation, bullets) are drawn with SF Pro, as
            # separate pieces in logical order so the RTL reversal below still places them right
            piece, has = '', None
            for ch in t:
                h = ord(ch) in self.script_cmap or _is_script(ch)
                if piece and h != has:
                    out.append((piece, self.script, 'rtl' if self.rtl else 'ltr') if has else (piece, self.latin, None))
                    piece = ''
                piece += ch; has = h
            if piece:
                out.append((piece, self.script, 'rtl' if self.rtl else 'ltr') if has else (piece, self.latin, None))
        return out[::-1] if self.rtl else out

    @staticmethod
    def _len(t, f, d):
        return f.getlength(t, direction=d) if d else f.getlength(t)

    def getlength(self, text):
        return sum(self._len(t, f, d) for t, f, d in self.runs(text))

    def getbbox(self, text, anchor='ls'):
        x, L, T, R, B = 0, None, None, None, None
        for t, f, d in self.runs(text):
            l, tp, r, b = f.getbbox(t, anchor=anchor, direction=d) if d else f.getbbox(t, anchor=anchor)
            L = x+l if L is None else min(L, x+l); R = x+r if R is None else max(R, x+r)
            T = tp if T is None else min(T, tp); B = b if B is None else max(B, b)
            x += self._len(t, f, d)
        return (L or 0, T or 0, R or 0, B or 0)

    def draw(self, d, xy, text, fill, anchor='ls'):
        x, y = xy
        for t, f, dr in self.runs(text):
            if dr:
                d.text((x, y), t, font=f, fill=fill, anchor=anchor, direction=dr)
            else:
                d.text((x, y), t, font=f, fill=fill, anchor=anchor)
            x += self._len(t, f, dr)


def font(role, size):
    return Font(role, size)


# ---------------------------------------------------------------- measuring
def _mask(a, box, thresh):
    x0, y0, x1, y1 = box
    reg = a[y0:y1, x0:x1].astype(int)
    border = np.concatenate([reg[0], reg[-1], reg[:, 0], reg[:, -1]])
    bg = np.median(border, 0)
    d = np.abs(reg - bg).sum(2)
    return d > thresh, bg, d


def measure(a, box, thresh=38):
    """Ink bbox (x0,y0,x1,y1), background colour, text colour inside box."""
    m, bg, d = _mask(a, box, thresh)
    ys, xs = np.where(m)
    if not len(xs):
        raise ValueError(f'no ink found in box {box}')
    x0, y0 = box[:2]
    bb = (int(xs.min()+x0), int(ys.min()+y0), int(xs.max()+x0+1), int(ys.max()+y0+1))
    strong = d >= np.percentile(d[m], 70)
    col = np.median(a[box[1]:box[3], box[0]:box[2]][strong], 0)
    return bb, bg, tuple(int(c) for c in col)


def fit_font(role, ref_text, bb, fixed=None):
    """Font size whose rendering of ref_text matches the original ink (width-first, since
    fonts differ in proportions). Returns font, baseline y, pen x, ink width."""
    f100 = font(role, 100)
    l, t, r, b = f100.getbbox(ref_text, anchor='ls')
    size_h = 100*(bb[3]-bb[1])/(b-t)
    size_w = 100*(bb[2]-bb[0])/(r-l)
    size = fixed or round(min(size_h, size_w))
    f = font(role, size)
    l, t, r, b = f.getbbox(ref_text, anchor='ls')
    return f, bb[3]-b, bb[0]-l, r-l


# ---------------------------------------------------------------- erasing
def erase(a, box, thresh=30, dil=6):
    """Remove ink in box; refill from the box's own background (normalized convolution),
    so neighbouring elements never bleed in."""
    x0, y0, x1, y1 = box
    m, _, _ = _mask(a, box, thresh)
    mask = cv2.dilate(m.astype(np.uint8), np.ones((2*dil+1, 2*dil+1), np.uint8)).astype(bool)
    reg = a[y0:y1, x0:x1].astype(float)
    w = (~mask).astype(float)
    fills = []
    for sig in (6, 18):
        num = np.stack([cv2.GaussianBlur(reg[..., c]*w, (0, 0), sig) for c in range(3)], -1)
        den = cv2.GaussianBlur(w, (0, 0), sig)[..., None]
        fills.append((num, den))
    (n1, d1), (n2, d2) = fills
    fill = np.where(d1 > 0.05, n1/np.maximum(d1, 1e-6), n2/np.maximum(d2, 1e-6))
    reg[mask] = fill[mask]
    a[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)


def erase_fit(a, box, thresh=30, dil=6, deg=2, fit_box=None):
    """Remove ink on a softly varying background (glow, dimmed overlay): fill from a
    low-order polynomial surface fitted to the non-ink pixels instead of a flat tone.
    Ink is detected inside box; the surface is fitted over fit_box (default box), which may
    be larger so the fit sees where a glow is heading."""
    m, _, _ = _mask(a, box, thresh)
    fb = fit_box or box
    x0, y0, x1, y1 = fb
    full_m = np.zeros((y1-y0, x1-x0), bool)
    full_m[box[1]-y0:box[3]-y0, box[0]-x0:box[2]-x0] = m
    mask = cv2.dilate(full_m.astype(np.uint8), np.ones((2*dil+1, 2*dil+1), np.uint8)).astype(bool)
    reg = a[y0:y1, x0:x1].astype(float)
    H, W = mask.shape
    yy, xx = np.mgrid[0:H, 0:W]; X, Y = xx/W, yy/H
    terms = [X**i*Y**j for i in range(deg+1) for j in range(deg+1) if i+j <= deg]
    A = np.stack([t[~mask] for t in terms], 1)
    full = np.stack([t.ravel() for t in terms], 1)
    with np.errstate(all='ignore'):
        for c in range(3):
            coef, *_ = np.linalg.lstsq(A, reg[..., c][~mask], rcond=None)
            reg[..., c][mask] = (full@coef).reshape(H, W)[mask]
    a[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)


def erase_vfill(a, rect, ink_box, thresh=30, dil=3):
    """Remove ink whose background changes left-to-right (e.g. fading into a glow): each
    column of rect is refilled by interpolating between the clean pixels above and below
    the ink, so horizontal ramps survive exactly. rect needs clean rows at top and bottom."""
    x0, y0, x1, y1 = rect
    m, _, _ = _mask(a, ink_box, thresh)
    full_m = np.zeros((y1-y0, x1-x0), bool)
    full_m[ink_box[1]-y0:ink_box[3]-y0, ink_box[0]-x0:ink_box[2]-x0] = m
    rows = np.where(cv2.dilate(full_m.astype(np.uint8), np.ones((2*dil+1, 2*dil+1), np.uint8)).any(1))[0]
    t, b = max(rows.min()-1, 0), min(rows.max()+1, y1-y0-1)
    reg = a[y0:y1, x0:x1].astype(float)
    w = ((np.arange(t, b+1)-t)/(b-t))[:, None, None]
    reg[t:b+1] = reg[t][None]*(1-w)+reg[b][None]*w
    a[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)


def erase_on_gradient(a, box, ink_sum=600, dil=6):
    """Large text on a smooth gradient: polynomial surface fit + low-frequency residual."""
    x0, y0, x1, y1 = box
    reg = a[y0:y1, x0:x1].astype(float)
    r, g, b = reg[..., 0], reg[..., 1], reg[..., 2]
    text = ((r+g+b) < ink_sum) | ((r < 120) & (g < 200))
    text = cv2.dilate(text.astype(np.uint8), np.ones((2*dil+1, 2*dil+1), np.uint8)).astype(bool)
    H, W = text.shape
    yy, xx = np.mgrid[0:H, 0:W]; X, Y = xx/W, yy/H
    terms = [X**i*Y**j for i in range(5) for j in range(5) if i+j <= 4]
    A = np.stack([t[~text] for t in terms], 1)
    full = np.stack([t.ravel() for t in terms], 1)
    fits = np.zeros_like(reg)
    with np.errstate(all='ignore'):  # harmless BLAS overflow warnings on some numpy builds
        for c in range(3):
            coef, *_ = np.linalg.lstsq(A, reg[..., c][~text], rcond=None)
            fits[..., c] = (full@coef).reshape(H, W)
    w = (~text).astype(float); res = (reg-fits)*w[..., None]
    num = np.stack([cv2.GaussianBlur(res[..., c], (0, 0), 35) for c in range(3)], -1)
    den = cv2.GaussianBlur(w, (0, 0), 35)[..., None]+1e-6
    out = reg.copy(); filled = fits+num/den
    out[text] = filled[text]
    a[y0:y1, x0:x1] = np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- drawing
def draw_text(img, xy, text, f, color, anchor='ls'):
    big = f.scaled(SS)
    l, t, r, b = big.getbbox(text, anchor=anchor)
    l, t, r, b = int(np.floor(l)), int(np.floor(t)), int(np.ceil(r)), int(np.ceil(b))
    pad = 8*SS
    w, h = r-l+2*pad, b-t+2*pad
    mask = Image.new('L', (w, h), 0)
    big.draw(ImageDraw.Draw(mask), (pad-l, pad-t), text, 255, anchor=anchor)
    mask = mask.resize((w//SS, h//SS), Image.LANCZOS)
    img.paste(Image.new('RGB', mask.size, tuple(color)),
              (round(xy[0]+(l-pad)/SS), round(xy[1]+(t-pad)/SS)), mask)


def resize_pill(a, pill, delta):
    """Grow/shrink a horizontal pill by delta px keeping its left edge (9-slice on columns)."""
    px0, py0, px1, py1 = pill
    if delta == 0:
        return
    mid, tail = (px0+px1)//2, px1+12
    band = a[py0:py1].copy()
    if delta > 0:
        W = a.shape[1]
        seg = band[:, mid:tail].copy()
        a[py0:py1, mid:min(mid+delta, W)] = np.repeat(band[:, mid:mid+1], min(delta, W-mid), 1)
        if mid+delta < W:
            a[py0:py1, mid+delta:min(tail+delta, W)] = seg[:, :min(tail+delta, W)-(mid+delta)]
        print(f'  NOTE pill {pill} grew by {delta}px to x1={px1+delta}')
    else:
        d = -delta
        a[py0:py1, mid:tail-d] = band[:, mid+d:tail]
        a[py0:py1, tail-d:tail] = np.repeat(band[:, tail:tail+1], d, 1)


def move_rect(src, a, rect, dx, fill):
    """Move an icon on a flat background (e.g. '+' on a button) horizontally by dx."""
    x0, y0, x1, y1 = rect
    icon = src[y0:y1, x0:x1].copy()
    a[y0:y1, x0:x1] = fill
    a[y0:y1, x0+dx:x1+dx] = icon


# ---------------------------------------------------------------- headline
def parse_headline(s):
    """Markup per line: *accent*  ^big^ (both may nest, e.g. ^*Track*^).
    -> list of lines, each a list of (text, colour, big)"""
    lines = []
    for line in s.split('\n'):
        parts, cur, acc, big = [], '', False, False
        for ch in line:
            if ch in '*^':
                if cur:
                    parts.append((cur, 'accent' if acc else 'dark', big)); cur = ''
                if ch == '*': acc = not acc
                else: big = not big
            else:
                cur += ch
        if cur:
            parts.append((cur, 'accent' if acc else 'dark', big))
        lines.append(parts)
    return lines


def _strip(t):
    return t.replace('*', '').replace('^', '')


def headline_plan(src, hl):
    """Measure the original headline lines -> sizes, baselines, centres.
    Layout options (all optional):
      sizes: [px per line]  explicit base size per line (else measured from line width)
      per_line_size: true    keep each line's measured size (default: median of all lines)
      big_size: px           size for ^big^ segments
      cxs: [x per line]      centre per line (default: common centre of the ink)"""
    role = hl.get('font', 'display_bold')
    metrics = []
    for i, (text, box) in enumerate(zip(hl['src_lines'], hl['line_boxes'])):
        m, _, _ = _mask(src, box, hl.get('thresh', 60))
        rows = m.sum(1); xs = np.where(m.any(0))[0]
        x0, x1 = box[0]+xs.min(), box[0]+xs.max()+1
        base = box[1]+np.where(rows >= 0.35*rows.max())[0].max()+1
        t_ = _strip(text)
        l, t, r, b = font(role, 100).getbbox(t_, anchor='ls')
        metrics.append((100*(x1-x0)/(r-l), base, (x0+x1)/2))
    if 'sizes' in hl:
        sizes = list(hl['sizes'])
    elif hl.get('per_line_size'):
        sizes = [round(m[0]) for m in metrics]
    else:
        sizes = [round(np.median([m[0] for m in metrics]))]*len(metrics)
    bases = [hl['bases'][i] if 'bases' in hl else m[1] for i, m in enumerate(metrics)]
    cxs = hl.get('cxs') or [hl.get('cx', float(np.mean([m[2] for m in metrics])))]*len(metrics)
    return role, sizes, bases, cxs


def _line_mask(segs, W=3000):
    im = Image.new('L', (W, 900), 0); d = ImageDraw.Draw(im); x = 20
    for t, f in segs:
        f.draw(d, (x, 600), t, 255); x += f.getlength(t)
    a = np.array(im) > 40
    return a, x-20


def draw_headline(img, src, hl, text, colors, max_width):
    role, sizes, bases, cxs = headline_plan(src, hl)
    lines = parse_headline(text)
    n = len(lines)
    if n != len(sizes):  # different line count: reuse last line's metrics
        sizes = (sizes+[sizes[-1]]*n)[:n]; cxs = (cxs+[cxs[-1]]*n)[:n]
        gap = (bases[-1]-bases[-2]) if len(bases) > 1 else sizes[0]
        bases = (bases+[bases[-1]+gap*(k+1) for k in range(n)])[:n]
    big = hl.get('big_size')
    out_sizes = []
    rendered = []
    for i, ln in enumerate(lines):
        s = sizes[i]
        segs = lambda sc: [(t, font(role, round((big if (b and big) else s)*sc))) for t, c, b in ln]
        w = sum(f.getlength(t) for t, f in segs(1))
        sc = min(1, max_width/w) if w else 1
        rendered.append((ln, segs(sc))); out_sizes.append(round(s*sc))
    # baselines: keep source rows; push down only when ink would touch the line above
    clear = hl.get('clear', 8)
    shift = 0; final = []
    for i, (ln, segs) in enumerate(rendered):
        base = bases[i]+shift
        if i:
            a1, w1 = _line_mask(rendered[i-1][1]); a2, w2 = _line_mask(segs)
            dx = round((cxs[i]-w2/2)-(cxs[i-1]-w1/2))
            a2 = np.roll(a2, dx, 1)
            grow = cv2.dilate(a1.astype(np.uint8), np.ones((2*clear+1, 2*clear+1), np.uint8)).astype(bool)
            g = round(base-final[-1])
            while g < 900:
                sh = np.zeros_like(a2)
                if g > 0: sh[g:] = a2[:-g]
                if not (grow & sh).any(): break
                g += 1
            shift += (final[-1]+g)-base; base = final[-1]+g
        final.append(base)
        w = sum(f.getlength(t) for t, f in segs)
        x = cxs[i]-w/2
        order = list(zip(ln, segs))
        if LANG == 'ar':  # right-to-left: the first segment ends up on the right
            order = order[::-1]
        for (t, c, b), (_, f) in order:
            draw_text(img, (x, base), t, f, colors[c]); x += f.getlength(t)
    return out_sizes


# ---------------------------------------------------------------- build
def load_json(p):
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


def build(layout_path, strings_path, out_path, verbose=True):
    L = load_json(layout_path)
    S = load_json(strings_path) if strings_path else {'strings': {}, 'headlines': {}}
    set_locale(S.get('locale'))
    # per-locale tweaks without touching the shared layout: {"NN": {"<item key>": {"size": 30}}}
    for k, o in S.get('layout_overrides', {}).get(os.path.splitext(os.path.basename(layout_path))[0], {}).items():
        if k == 'headline':
            L['headline'].update(o); continue
        hits = [it for it in L['items'] if it.get('key', it['src']) == k]
        if not hits:
            raise SystemExit(f'layout_overrides: no item {k!r} in {layout_path}')
        for it in hits:
            it.update(o)
    base_dir = os.path.dirname(os.path.abspath(layout_path))
    src_path = os.path.normpath(os.path.join(base_dir, L['source']))
    src_img = Image.open(src_path)
    src = np.array(src_img.convert('RGB'))
    a = src.copy()
    tr = S.get('strings', {})
    missing = []

    def T(it):
        key = it.get('key', it['src'])
        if key not in tr:
            missing.append(key)
        return tr.get(key, it['src'])

    # 1) measure on pristine source
    plan = []
    for it in L['items']:
        bb, bg, col = measure(src, it['box'], it.get('thresh', 38))
        f, base, left, w_old = fit_font(it['weight'], it['src'], bb, it.get('size'))
        plan.append(dict(it=it, bb=bb, f=f, base=base, left=left, col=tuple(it.get('color', col)), dst=T(it)))
    # shared size / baseline inside groups (weekday labels, tab bar, identical tags)
    for g, opt in L.get('groups', {}).items():
        mem = [p for p in plan if p['it'].get('group') == g]
        if not mem:
            continue
        if opt.get('share_size'):
            s = int(np.median([p['f'].size for p in mem])+0.5)
            for p in mem:
                if 'size' not in p['it']:
                    f, base, left, _ = fit_font(p['it']['weight'], p['it']['src'], p['bb'], s)
                    p.update(f=f, base=base, left=left)
        if opt.get('share_base'):
            b = float(np.median([p['base'] for p in mem]))
            for p in mem:
                p['base'] = b
    # 2) erase
    for it in L['items']:
        if it.get('erase') == 'vfill':
            erase_vfill(a, it.get('erase_rect', it['box']), it['box'], min(it.get('thresh', 38), 30))
        elif it.get('erase') == 'fit':
            erase_fit(a, it['box'], min(it.get('thresh', 38), 30), deg=it.get('fit_deg', 2), fit_box=it.get('fit_box'))
        else:
            erase(a, it['box'], min(it.get('thresh', 38), 30))
    # 3) pills + buttons, 4) draw
    img = None
    pushes = []  # (region, dx): content already shifted right by an earlier pill
    for p in plan:
        it, f = p['it'], p['f']
        shift = sum(d for (x0, y0, x1, y1), d in pushes
                    if it['box'][0] >= x0 and it['box'][1] < y1 and it['box'][3] > y0)
        l, t, r, b = f.getbbox(p['dst'], anchor='ls')
        if it.get('align') == 'center':
            cx = it.get('cx', (p['bb'][0]+p['bb'][2])/2)
            p['x'] = cx-(r-l)/2-l
        elif it.get('align') == 'right':
            p['x'] = it.get('rx', p['bb'][2])-r
        else:
            p['x'] = p['left']
        if 'button' in it:  # re-centre [icon + label] inside the button
            bt = it['button']; ix0 = bt['icon'][0]
            new_right = p['x']+r
            dx = round(((bt['x0']+bt['x1'])/2) - (ix0+new_right)/2)
            move_rect(src, a, bt['icon'], dx, bt['fill'])
            p['x'] += dx
        if 'x' in it:  # explicit ink-left x (text whose original ink is partly hidden)
            p['x'] = it['x']-l
        p['x'] += it.get('dx', 0)+shift
        if 'pill' in it and it.get('pill_anchor') == 'right':
            # right edge fixed: text keeps its right padding, pill grows/shrinks to the left
            p['x'] = p['bb'][2]-r
            delta = round(p['bb'][0]-(p['x']+l))
            W = a.shape[1]; px0, py0, px1, py1 = it['pill']
            m = a[:, ::-1].copy()
            resize_pill(m, [W-px1, py0, W-px0, py1], delta)
            a[:] = m[:, ::-1]
        else:
            delta = round((p['x']+r) - p['bb'][2]-shift)
            if 'push' in it and delta > 0:
                # neighbours to the right (next chips in a row, '• ⚠ 1 left' after a label)
                # move along so the longer text does not run into them
                x0, y0, x1, y1 = it['push']
                a[y0:y1, x0+delta:x1] = a[y0:y1, x0:x1-delta].copy()
                a[y0:y1, x0:x0+delta] = np.repeat(a[y0:y1, x0:x0+1], delta, 1)
                pushes.append((it['push'], delta))
            if 'pill' in it:  # pill hugs the new text with the original right padding
                px0, py0, px1, py1 = it['pill']
                resize_pill(a, [px0+shift, py0, px1+shift, py1], delta)
        p['base'] = it.get('base', p['base'])
    hl = L.get('headline')
    if hl:
        er = hl['erase']
        for box in (er if isinstance(er[0], list) else [er]):
            erase_on_gradient(a, box, hl.get('ink_sum', 600))
    img = Image.fromarray(a)
    for p in plan:
        it = p['it']
        if 'clip' in it:
            # text running under an overlay (card on top of a phone): draw, then keep only the
            # part inside clip, fading out over the last `fade` px like the original glow
            cx0, cy0, cx1, cy1 = it['clip']; fade = it.get('fade', 0)
            before = np.array(img).astype(float)
            draw_text(img, (p['x'], p['base']), p['dst'], p['f'], p['col'])
            after = np.array(img).astype(float)
            al = np.zeros(before.shape[:2])
            ramp = np.ones(cx1-cx0)
            if fade:
                ramp[-fade:] = np.linspace(1, 0, fade)
            al[cy0:cy1, cx0:cx1] = ramp
            img = Image.fromarray(np.clip(before+(after-before)*al[..., None], 0, 255).astype(np.uint8))
            continue
        draw_text(img, (p['x'], p['base']), p['dst'], p['f'], p['col'])
        if verbose:
            print(f"  {p['it']['src']!r:26} -> {p['dst']!r:26} size={p['f'].size}")
    if hl:
        key = hl.get('key', os.path.splitext(os.path.basename(layout_path))[0])
        text = S.get('headlines', {}).get(key)
        if text is None:
            missing.append(f'headlines.{key}')
            text = '\n'.join(hl['src_lines'])
        colors = {k: tuple(v) for k, v in hl['colors'].items()}
        size = draw_headline(img, src, hl, text, colors, hl.get('max_width', a.shape[1]-220))
        if verbose:
            print(f"  headline -> {text!r} size={size}")
    out = img.convert('RGBA') if src_img.mode == 'RGBA' else img
    if src_img.mode == 'RGBA':
        out.putalpha(src_img.getchannel('A'))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    out.save(out_path)
    if verbose:
        print(f'  font={FONT_NAME}  size={out.size}  -> {out_path}')
        if missing and strings_path:
            print(f'  WARNING untranslated (kept source text): {sorted(set(missing))}')
    return out, sorted(set(missing))
