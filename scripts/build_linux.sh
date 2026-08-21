#!/usr/bin/env bash
# Build PeerCode for Linux: standalone binary + .desktop launcher packaged in a tar.gz
# Run on Linux with Python 3.10+, Node.js 18+, and PyGObject (python3-gi) for the native window.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/4] Building web UI..."
(cd webapp && npm install && npm run build)

echo "[2/4] Installing Python build deps..."
python3 -m pip install --quiet pyinstaller pywebview aiohttp websockets watchdog

echo "[3/4] Building binary..."
pyinstaller --noconfirm --onefile --windowed --name PeerCode \
  --icon assets/icon_512.png \
  --add-data "web:web" \
  --add-data "backend:backend" \
  --collect-all webview \
  app.py

echo "[4/4] Packaging..."
STAGE="dist/PeerCode-linux-x64"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp dist/PeerCode "$STAGE/"
cp assets/icon_512.png "$STAGE/peercode.png"

cat > "$STAGE/peercode.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=PeerCode
Comment=Secure LAN collaborative code editor
Exec=PeerCode
Icon=peercode
Terminal=false
Categories=Development;IDE;Network;
DESKTOP

cat > "$STAGE/README.txt" <<'TXT'
PeerCode for Linux
==================
1. Move these files somewhere permanent, e.g.:
     sudo mv PeerCode /usr/local/bin/
     sudo mkdir -p /usr/share/icons/hicolor/512x512/apps
     sudo cp peercode.png /usr/share/icons/hicolor/512x512/apps/
     sudo mkdir -p ~/.local/share/applications
     sudo cp peercode.desktop ~/.local/share/applications/

2. Launch "PeerCode" from your app menu, or run ./PeerCode.

Requirements: WebKitGTK (libwebkit2gtk-4.1) for the native window.
On Debian/Ubuntu:  sudo apt install libwebkit2gtk-4.1-0
On Fedora:         sudo dnf install webkit2gtk4.1
If the native window is unavailable, PeerCode falls back to your browser.
TXT

tar -czf dist/PeerCode-linux-x64.tar.gz -C dist "$(basename "$STAGE")"

echo "Done: dist/PeerCode-linux-x64.tar.gz"
