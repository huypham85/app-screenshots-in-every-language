#!/bin/bash
# setup.sh — prepare the Python environment appshotkit's scripts run in.
# Prints the interpreter path on the last line; use it for every script.
#
#   PY=$(bash scripts/setup.sh | tail -1)
set -euo pipefail
VENV="${APPSHOTKIT_VENV:-$HOME/.cache/appshotkit/venv}"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV" >&2
fi
if ! "$VENV/bin/python" -c "import PIL, numpy, cv2, fontTools" 2>/dev/null; then
  echo "appshotkit: installing Pillow, NumPy, OpenCV, fontTools into $VENV (first run only)" >&2
  "$VENV/bin/python" -m pip install -q --disable-pip-version-check \
    pillow numpy opencv-python-headless fonttools >&2
fi

# Arabic/Devanagari shaping needs Pillow's raqm layout, which needs FriBiDi.
if ! "$VENV/bin/python" -c "from PIL import features; import sys; sys.exit(0 if features.check('raqm') else 1)" 2>/dev/null; then
  echo "note: complex scripts (Arabic, Hindi) need FriBiDi: brew install fribidi" >&2
fi
# SF Pro gives the exact iOS look; Inter (bundled) is the fallback.
if [ ! -f /Library/Fonts/SF-Pro-Text-Regular.otf ] && [ ! -f "$HOME/Library/Fonts/SF-Pro-Text-Regular.otf" ]; then
  echo "note: SF Pro not installed (developer.apple.com/fonts); using bundled Inter" >&2
fi
if [ ! -d "/Applications/Google Chrome.app" ]; then
  echo "note: Google Chrome not found; compose needs it to render HTML frames" >&2
fi
RAQM=$("$VENV/bin/python" -c "from PIL import features; print('yes' if features.check('raqm') else 'no')" 2>/dev/null)
FONT="Inter (bundled)"; { [ -f /Library/Fonts/SF-Pro-Text-Regular.otf ] || [ -f "$HOME/Library/Fonts/SF-Pro-Text-Regular.otf" ]; } && FONT="SF Pro"
echo "appshotkit: python ok · font: $FONT · Arabic/Hindi shaping: $RAQM" >&2
echo "$VENV/bin/python"
