#!/usr/bin/env bash
# Build PeerCode for macOS: PeerCode.app bundle + PeerCode.dmg
# Run on a Mac with Python 3.10+, Node.js 18+ and Xcode command line tools installed.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[1/4] Building web UI..."
(cd webapp && npm install && npm run build)

echo "[2/4] Installing Python build deps..."
python3 -m pip install --quiet pyinstaller pywebview aiohttp websockets watchdog

echo "[3/4] Building PeerCode.app..."
APP="dist/PeerCode.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

pyinstaller --noconfirm --onefile --windowed --name PeerCode \
  --icon assets/icon_512.png \
  --add-data "web:web" \
  --add-data "backend:backend" \
  --collect-all webview \
  app.py

mv dist/PeerCode "$APP/Contents/MacOS/PeerCode"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>              <string>PeerCode</string>
    <key>CFBundleDisplayName</key>       <string>PeerCode</string>
    <key>CFBundleIdentifier</key>        <string>org.peercode.app</string>
    <key>CFBundleVersion</key>           <string>1.0.0</string>
    <key>CFBundleShortVersionString</key><string>1.0.0</string>
    <key>CFBundleExecutable</key>        <string>PeerCode</string>
    <key>CFBundlePackageType</key>       <string>APPL</string>
    <key>CFBundleIconFile</key>          <string>PeerCode.icns</string>
    <key>NSHighResolutionCapable</key>   <true/>
    <key>LSMinimumSystemVersion</key>    <string>10.13</string>
</dict>
</plist>
PLIST

# App icon (.icns from the PNG set)
mkdir -p "$APP/Contents/Resources/PeerCode.iconset"
for s in 16 32 64 128 256 512; do
  cp "assets/icon_${s}.png" "$APP/Contents/Resources/PeerCode.iconset/icon_${s}x${s}.png" 2>/dev/null || true
done
if command -v iconutil >/dev/null 2>&1; then
  iconutil -c icns "$APP/Contents/Resources/PeerCode.iconset" \
           -o "$APP/Contents/Resources/PeerCode.icns"
fi
rm -rf "$APP/Contents/Resources/PeerCode.iconset"

echo "[4/4] Creating DMG..."
hdiutil create -volname PeerCode -srcfolder "$APP" -ov -format UDZO dist/PeerCode.dmg

echo "Done: $APP and dist/PeerCode.dmg"
