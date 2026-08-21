"""PeerCode desktop shell.

Runs the collaboration backend locally and opens the bundled web UI inside a
native desktop window (WebView2 via pywebview). If the native window cannot be
created (e.g. WebView2 runtime missing), it falls back to opening the default
browser with a small control window. Works from source and as a frozen exe.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

UI_URL = "http://127.0.0.1:7432/"
WINDOW_BG = "#090B0F"


def resource_base() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


def server_ready(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", 7432), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def run_server() -> None:
    base = resource_base()
    sys.path.insert(0, str(base / "backend"))
    os.environ["PEERCODE_WEB_ROOT"] = str(base / "web")

    # windowed executables have no console streams
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    import asyncio

    from main import main as backend_main

    try:
        asyncio.run(backend_main())
    except Exception as exc:  # port busy, etc.
        _show_error(str(exc))
        os._exit(1)


def _show_error(message: str) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("PeerCode", f"Could not start PeerCode:\n{message}")
        root.destroy()
    except Exception:
        print(f"PeerCode error: {message}", file=sys.stderr)


def open_ui() -> None:
    if server_ready():
        webbrowser.open(UI_URL)


def run_native_window() -> bool:
    """Open the UI in a native desktop window. Returns False if unavailable."""
    try:
        import webview

        webview.create_window(
            "PeerCode",
            UI_URL,
            width=1366,
            height=850,
            min_size=(980, 640),
            background_color=WINDOW_BG,
        )
        webview.start()
        return True
    except Exception as exc:
        print(f"native window unavailable: {exc}", file=sys.stderr)
        return False


def run_control_window(on_open) -> None:
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("PeerCode")
    root.geometry("340x170")
    root.resizable(False, False)
    root.eval("tk::PlaceWindow . center")

    frame = ttk.Frame(root, padding=24)
    frame.pack(fill="both", expand=True)

    header = ttk.Frame(frame)
    header.pack(pady=(0, 4))
    logo = tk.Canvas(header, width=34, height=34, highlightthickness=0)
    logo.pack(side="left", padx=(0, 10))
    logo.create_oval(0, 0, 34, 34, fill="#E8B15A", outline="")
    logo.create_text(17, 17, text="P", font=("Georgia", 15, "bold"), fill="#1c1408")
    ttk.Label(header, text="PeerCode", font=("Segoe UI", 14, "bold")).pack(side="left")

    ttk.Label(
        frame,
        text=f"Serving your session UI at\n{UI_URL}",
        foreground="#777777",
        justify="center",
    ).pack(pady=6)

    ttk.Button(frame, text="Open App", command=on_open).pack(fill="x", pady=3)
    ttk.Button(frame, text="Quit PeerCode", command=os._exit).pack(fill="x", pady=3)

    def on_close():
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


def main() -> None:
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    if not server_ready():
        _show_error("The PeerCode backend failed to start. Port 7432 may be in use.")
        os._exit(1)

    # Native desktop window; falls back to browser + control window.
    if not run_native_window():
        threading.Thread(target=open_ui, daemon=True).start()
        run_control_window(open_ui)

    os._exit(0)


if __name__ == "__main__":
    main()
