<div align="center">

# PeerCode

**A collaborative code editor that stays local.**

PeerCode operates using a lightweight Host/Guest architecture, all contained within the same Python application. When a user creates a session, their client becomes the Host, and other clients on the local network become Guests.

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![React](https://img.shields.io/badge/UI-React%20%2B%20Tailwind%20%2B%20Motion-61DAFB)

</div>

---

## ✨ What is PeerCode?

PeerCode turns any folder on your machine into a shared workspace. Host a session, and teammates on the
**same Wi-Fi** join with a short code — everyone edits the same file in real time, sees each other's
cursors, and browses the project tree together.

```
┌─────────────┐         same Wi-Fi          ┌─────────────┐
│   Host 💻   │ ◄──── 6-char code ────►     │  Guests 💻💻 │
│  session:   │      A7X9QP + port          │  live sync  │
│  A7X9QP     │      (auto-discovered)      │             │
└─────────────┘                             └─────────────┘
```

### Highlights

- 🚀 **One-click hosting** — pick a folder (native file dialog), get an invite
- 🔐 **Secure by design** — random 256-bit session key per session, handshake validation, unauthenticated packets ignored, JSON-only protocol (no pickle/eval)
- ⚡ **Real-time sync** — incremental insert/delete operations (not full-file dumps), cursor presence, live peer list
- 🧭 **Auto-discovery** — guests only need your IP and code; the port is found automatically via LAN broadcast
- 🎨 **5 cozy themes** — Ember, Daylight, Nordic, Rosewood, Forest — full glassmorphism UI with Motion-powered micro-interactions
- 🖥️ **True desktop app** — native window via WebView2 / WKWebView / WebKitGTK, with browser fallback

## 📦 Download & Install

Grab the latest build for your platform from **[Releases](../../releases)**:

| Platform | File | Install |
|---|---|---|
| **Windows** | `PeerCode-Setup.exe` | Run it. Next → Next → Done. Desktop shortcut optional |
| **Windows** (portable) | `PeerCode.exe` | Just run it — no install needed |
| **macOS** | `PeerCode.dmg` | Open, drag **PeerCode.app** to Applications |
| **Linux** | `PeerCode-linux-x64.tar.gz` | See `README.txt` inside (binary + `.desktop` entry) |

> **Requirements:** all runtime dependencies are bundled. Linux needs `libwebkit2gtk` for the native window (`sudo apt install libwebkit2gtk-4.1-0`) — otherwise PeerCode falls back to your browser automatically.

## 🖥️ Using PeerCode

1. **Host Session** → choose a folder → you get a session code, your IP and port
2. Hit **Copy Invite** and send `IP + Code` to teammates on the same network
3. They hit **Join Session**, enter both, and you're editing together instantly
4. `Ctrl+S` saves; conflicts are detected and resolved with one click
5. **End Session** disconnects everyone cleanly

## 🎨 Themes

Switch anytime from the editor toolbar or Settings — your choice is remembered:

| Ember *(default)* | Daylight | Nordic | Rosewood | Forest |
|:-:|:-:|:-:|:-:|:-:|
| Dark charcoal + warm amber | Cozy paper light | Deep blue slate | Dark plum rose | Deep forest green |

## 🛠️ Build from Source

### Run in dev mode

```bash
# terminal 1 — backend
cd backend
pip install -r requirements.txt
python main.py            # serves everything at http://127.0.0.1:7432

# terminal 2 — frontend (hot reload)
cd webapp
npm install
npm run dev               # http://localhost:5183, proxies API to :7432
```

Or simply run the desktop shell from source:

```bash
pip install aiohttp websockets watchdog pywebview
python app.py             # native window + backend
```

### Build installers

| OS | Command | Output |
|---|---|---|
| Windows | `scripts\build_windows.bat` | `dist\PeerCode.exe` + `dist\installer\PeerCode-Setup.exe` |
| macOS | `bash scripts/build_macos.sh` | `dist/PeerCode.app` + `dist/PeerCode.dmg` |
| Linux | `bash scripts/build_linux.sh` | `dist/PeerCode-linux-x64.tar.gz` |

Prerequisites: Python 3.10+, Node.js 18+. Windows builds additionally need [Inno Setup 6](https://jrsoftware.org/isinfo.php).

## 🏗️ Architecture

```
peercode/
├── app.py                  # desktop shell: backend + native window (pywebview)
├── assets/                 # app icons (.ico / .png)
├── backend/                # Python backend (aiohttp + websockets)
│   ├── main.py             # HTTP server, serves the built UI
│   ├── bridge.py           # REST + WebSocket bridge between UI and sessions
│   ├── host.py             # session host: auth, broadcast, file ops
│   ├── guest.py            # session guest: connect, receive, request
│   ├── security.py         # session codes, keys, registry, path safety
│   ├── sync_engine.py      # incremental text-sync operations
│   ├── discovery.py        # LAN auto-discovery (UDP broadcast)
│   ├── watcher.py          # external file-change tracking
│   └── test_collaboration.py
├── webapp/                 # React + Tailwind v4 + Motion frontend
│   └── src/
│       ├── components/     # GlassCard, GlassButton, Sidebar, Toast, ...
│       └── screens/        # Launch, Host, Join, Workspace
├── installer/              # Inno Setup script (Windows)
├── scripts/                # build scripts for all platforms
└── web/                    # production build output (served by backend)
```

**How a session works:**

1. The host generates a random 6-char code (`A-Z`, `2-9`, no confusing chars), a random port (45000–55000) and a 256-bit key — all in memory, never persisted
2. It broadcasts announcements on the LAN so joiners can resolve the port from just IP + code
3. Guests complete a validated handshake; every further message is checked against the session key and an allow-list of message types
4. Edits travel as small JSON operations (`insert` / `delete` / `replace`), applied through a lock-protected sync engine

## 🔒 Security notes

- Session keys are cryptographically random (`secrets`), compared in constant time
- Unknown clients are rejected at the handshake; packets from unauthenticated peers are dropped
- All file access is sandboxed to the shared folder (path-traversal protected)
- Everything stays on your LAN — nothing ever touches the internet

