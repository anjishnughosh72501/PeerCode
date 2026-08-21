from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from aiohttp import web

from bridge import Bridge

if sys.stdout:  # stdout is None in windowed (frozen) builds
    sys.stdout.reconfigure(line_buffering=True)
os.environ["PYTHONUNBUFFERED"] = "1"


def web_root() -> Path:
    env = os.environ.get("PEERCODE_WEB_ROOT")
    if env:
        return Path(env)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "web"
    return Path(__file__).resolve().parent.parent / "web"


async def health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "app": "peercode"})


async def web_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(web_root() / "index.html")


async def on_startup(app: web.Application) -> None:
    print(json.dumps({"status": "ready", "port": 7432, "app": "peercode"}), flush=True)


async def main() -> None:
    bridge = Bridge()
    root = web_root()
    bridge.app.router.add_get("/", web_index)
    bridge.app.router.add_get("/app", web_index)
    bridge.app.router.add_static("/web", root)
    bridge.app.router.add_get("/health", health)
    bridge.app.on_startup.append(on_startup)
    await bridge.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(json.dumps({"status": "error", "app": "peercode", "message": str(e)}), flush=True)
        sys.exit(1)
