#!/bin/bash
# render.sh — render a local HTML file to a PNG with headless Chrome.
#
#   render.sh <in.html> <out.png> [width] [height]      (default 1290 2796, iPhone 6.9")
#
# Local files next to the HTML (images, CSS, fonts) load via file://.
set -euo pipefail
IN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; OUT="$2"; W="${3:-1290}"; H="${4:-2796}"
CH="${CHROME:-}"
for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
         "/Applications/Chromium.app/Contents/MacOS/Chromium" \
         "$(command -v google-chrome 2>/dev/null || true)" "$(command -v chromium 2>/dev/null || true)"; do
  [ -z "$CH" ] && [ -n "$c" ] && [ -x "$c" ] && CH="$c"
done
[ -z "$CH" ] && { echo "Chrome/Chromium not found (set CHROME=/path/to/binary)" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"
"$CH" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --allow-file-access-from-files --window-size="$W,$H" --default-background-color=00000000 \
  --virtual-time-budget=4000 --screenshot="$OUT" "file://$IN" >/dev/null 2>&1
[ -s "$OUT" ] || { echo "render failed: $IN" >&2; exit 1; }
echo "$OUT"
