#!/usr/bin/env bash
# ============================================================
#  PeerCode one-command setup for macOS and Linux
#  Installs every dependency and launches the app from source.
#  Works on a fresh clone - no prebuilt artifacts required.
#
#  Usage:  ./setup.sh [--no-run]
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
            PYTHON="$candidate"
            break
        fi
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.9+ was not found on PATH."
    echo "Install it from https://www.python.org/downloads/ (macOS/Linux: your package manager works too)."
    exit 1
fi
echo "[PeerCode] Found $($PYTHON --version)"

echo "[PeerCode] Creating virtual environment..."
if [ ! -d .venv ]; then
    "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[PeerCode] Installing backend dependencies..."
python -m pip install --upgrade pip --quiet
pip install -r backend/requirements.txt

# Optional: native desktop window (falls back to your browser without it)
pip install pywebview --quiet >/dev/null 2>&1 \
    || echo "[PeerCode] pywebview unavailable - the UI will open in your browser instead."

echo "[PeerCode] Building web UI..."
if command -v npm >/dev/null 2>&1; then
    (cd webapp && npm install --no-audit --no-fund && npm run build)
else
    echo "Node.js not found - using the prebuilt web bundle in web/."
fi

if [ "${1:-}" = "--no-run" ]; then
    echo "[PeerCode] Setup complete (launch later with: source .venv/bin/activate && python app.py)"
    exit 0
fi

echo
echo "============================================"
echo "  PeerCode is ready! Starting it now..."
echo "  The UI opens at http://127.0.0.1:7432/"
echo "============================================"
echo
python app.py
