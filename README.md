<div align="center">

# PeerCode

### Real-time collaborative coding — entirely on your local network.

No accounts. No cloud. Just open a session and code together.

Python 3.9+ &nbsp;·&nbsp; Windows · macOS · Linux

</div>

---

## ⚠️ Important Note: Wi-Fi/LAN Only

**PeerCode is a strictly local tool.** It only works if all devices are connected to the **same Wi-Fi network (LAN)**. It does not use any external servers, so it cannot connect devices across the internet.

---

## How It Works (Architecture Overview)

PeerCode operates using a lightweight Host/Guest architecture, all contained within the same Python application. When a user creates a session, their client becomes the **Host**, and other clients on the local network become **Guests**.

### 1. Zero-Configuration LAN Discovery (`discovery.py`)
To eliminate the need for users to type IP addresses, the Host continuously broadcasts its presence over the local network using **UDP Broadcasts** on port `21000`. 
- The broadcast payload is a JSON packet containing the session name, a secure 6-character session code, and the dynamic TCP port the Host is listening on.
- When a Guest attempts to join, their client listens for these UDP broadcasts and automatically extracts the Host's IP and port, matching it against the session code provided by the user.

### 2. WebSocket Protocol & Async Server (`host.py` & `guest.py`)
Once discovered, the Guest connects to the Host via a custom **WebSocket protocol** built on top of `asyncio` and `websockets`.
- **Event-Driven:** The server uses `asyncio` to handle multiple peer connections concurrently without blocking the main GUI thread.
- **Security:** Each session is protected by a randomly generated 6-character alphanumeric code. For subsequent requests, an underlying 256-bit hexadecimal session key is used to authenticate messages to prevent hijacking (`security.py`).

### 3. File System Synchronization (`sync_engine.py` & `watcher.py`)
Keeping files in sync across multiple clients is handled via a two-pronged approach:
- **Internal Edits:** When a user types in the built-in Tkinter editor, the `SyncEngine` translates these into atomic JSON operations (e.g., `{"op": "insert", "index": 10, "text": "foo"}`). These operations are base64-encoded, sent to the Host, and broadcast to all other Guests to apply to their local state.
- **External Edits:** If you open the project folder in VS Code or another IDE, the `FileWatcher` uses the `watchdog` library to monitor the file system for external changes. When a modification is detected, the Host reads the updated file, increments the file version, and broadcasts a `FILE_UPDATE` event to forcefully sync all peers.

### 4. Browser Client (`webapp/`)
In addition to the desktop app, PeerCode ships a lightweight **browser-based client** built with React + Vite. Guests can join a session from any device with a web browser — no installation required — and get the same real-time editing experience through the same WebSocket protocol.

---

## Tech Stack

| Component | Technology |
|---|---|
| **Desktop GUI** | Python + `Tkinter` (Zero external dependencies for GUI) |
| **Web Client** | React + Vite (`webapp/`) |
| **Network Protocol** | `asyncio`, `aiohttp`, `websockets` |
| **File Syncing** | `watchdog` (Observer-based filesystem tracking) |
| **Packaging** | `PyInstaller` (Bundles Python environment & dependencies) |

---

## Quick Start

### Option 1: Using the Prebuilt Executable (Windows)

1. Download `PeerCode.exe` from the `dist/` directory (or Releases).
2. Run it — everything is bundled, no Python installation needed.
3. Launch PeerCode and start or join a session.

### Option 2: Run from source

```bash
# 1. Clone the repo
git clone https://github.com/anjishnughosh72501/PeerCode.git
cd PeerCode

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Launch
python app.py
```

---

## Building the Executable

**Important:** PyInstaller is not a cross-compiler. To create a macOS executable, you must run these commands on a Mac. To create a Linux executable, you must run them on Linux.

### Windows

```bash
# 1. Build the main application
pyinstaller --onefile --windowed --name PeerCode --icon=assets/Peercodelogo.ico --paths backend --hidden-import websockets --hidden-import aiohttp --hidden-import watchdog --hidden-import tkinter app.py
```

To create the end-user installer, build the bundled executable first, then compile the Inno Setup script:

```bash
# 2. Build the setup installer (requires Inno Setup)
iscc installer/PeerCode.iss
```

### macOS & Linux

```bash
pyinstaller --onefile --windowed --name PeerCode --paths backend --hidden-import websockets --hidden-import aiohttp --hidden-import watchdog --hidden-import tkinter app.py
```

---

<div align="center">

Built for developers who just want to code together.

</div>
