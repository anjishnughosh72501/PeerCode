from __future__ import annotations

import asyncio
import json
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable

from aiohttp import WSMsgType, web

from discovery import Listener, get_local_ip
from guest import Guest, GuestConnectionError
from host import Host
from security import PORT_MAX, PORT_MIN, validate_ip, validate_session_code

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


class Bridge:
    def __init__(self) -> None:
        self.host: Host | None = None
        self.guest: Guest | None = None
        self.flutter_sockets: set[web.WebSocketResponse] = set()
        self.discovered: dict[str, dict[str, Any]] = {}
        self.loop: asyncio.AbstractEventLoop | None = None
        self.listener = Listener(self._on_discovered, self._on_lost)
        self.peer_cache: list[dict[str, Any]] = []

        self.app = web.Application(middlewares=[self._error_middleware])
        self.app.add_routes(
            [
                web.post("/host", self.host_project),
                web.post("/dialog/folder", self.pick_folder),
                web.post("/guest/validate", self.validate_guest),
                web.post("/guest/connect", self.connect_guest),
                web.post("/guest/approve", self.approve_guest),
                web.post("/kick", self.kick_user),
                web.post("/project/tree", self.project_tree),
                web.post("/file/read", self.read_file),
                web.post("/file/write", self.write_file),
                web.post("/file/create", self.create_node),
                web.post("/file/rename", self.rename_node),
                web.post("/file/delete", self.delete_node),
                web.post("/file/active", self.set_active_file),
                web.post("/text/edit", self.text_edit),
                web.post("/cursor", self.cursor),
                web.post("/disconnect", self.disconnect),
                web.get("/session", self.session_info),
                web.get("/peers", self.peers),
                web.get("/ws", self.ws),
            ]
        )

    @web.middleware
    async def _error_middleware(self, request: web.Request, handler: Handler) -> web.StreamResponse:
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except GuestConnectionError as exc:
            return web.json_response({"status": "error", "message": str(exc)}, status=400)
        except Exception as exc:
            await self.push_to_flutter({"type": "error", "message": str(exc)})
            return web.json_response({"status": "error", "message": str(exc)}, status=500)

    async def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.listener.start()
        runner = web.AppRunner(self.app)
        await runner.setup()
        port = int(os.environ.get("PEERCODE_PORT", "7432"))
        site = web.TCPSite(runner, "127.0.0.1", port)
        await site.start()
        print(f"PeerCode backend ready on port {port}", flush=True)
        while True:
            await asyncio.sleep(3600)

    async def pick_folder(self, request: web.Request) -> web.Response:
        """Open a native folder picker on this machine and return the selection."""
        self._dialog_lock = getattr(self, "_dialog_lock", threading.Lock())

        def _pick_webview() -> str:
            import webview

            windows = list(webview.windows)
            if not windows:
                raise RuntimeError("no webview window")
            result = windows[0].create_file_dialog(webview.FOLDER_DIALOG)
            if not result:
                return ""
            return str(result[0])

        def _pick_tkinter() -> str:
            import tkinter as tk
            from tkinter import filedialog

            with self._dialog_lock:
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                root.lift()
                root.focus_force()
                try:
                    return filedialog.askdirectory(title="Choose a folder to share", parent=root) or ""
                finally:
                    root.destroy()

        loop = asyncio.get_running_loop()
        try:
            path = await loop.run_in_executor(None, _pick_webview)
        except Exception:
            try:
                path = await loop.run_in_executor(None, _pick_tkinter)
            except Exception as exc:
                return web.json_response({"status": "error", "message": str(exc)}, status=500)
        return web.json_response({"status": "ok", "path": path})

    async def host_project(self, request: web.Request) -> web.Response:
        data = await request.json()
        name = str(data.get("name", "Host"))
        filepath = str(data["filepath"])

        if self.host or self.guest:
            await self._stop_session()

        self.host = Host(project_path=filepath, name=name)
        self.host.on_file_change = lambda path, content, version: self._schedule(
            {"type": "file_update", "path": path, "content": content, "version": version}
        )
        self.host.on_text_edit = lambda path, op, author: self._schedule(
            {"type": "text_edit", "path": path, "op": op, "author": author}
        )
        self.host.on_active_file = lambda path, content, version: self._schedule(
            {"type": "active_file", "path": path, "content": content, "version": version}
        )
        self.host.on_peer_list = lambda peers: self._update_peers(peers)
        self.host.on_cursor = lambda payload: self._schedule({"type": "cursor_update", **payload})
        self.host.on_error = lambda message: self._schedule({"type": "error", "message": message})
        self.host.on_session_closed = lambda: self._schedule(
            {"type": "session_closed", "message": "Session ended"}
        )
        self.host.on_join_request = lambda request_id, name: self._schedule(
            {"type": "join_request", "request_id": request_id, "name": name}
        )
        self.host.on_join_resolved = lambda request_id, name, approved: self._schedule(
            {"type": "join_resolved", "request_id": request_id, "name": name, "approved": approved}
        )

        self.host.start()
        self.peer_cache = self.host.peer_list()
        info = self.host.get_session_info()

        return web.json_response(
            {
                "status": "ok",
                "ip": info["ip"],
                "port": info["port"],
                "code": info["code"],
                "session_id": info["session_id"],
                "project_name": self.host.project_name,
            }
        )

    async def _locate_host(self, host_ip: str, code: str, host_port: int = 0) -> int:
        """Resolve the host TCP port: explicit port -> discovery cache (with a
        short wait for late announces) -> direct TCP scan of the app's port range."""
        if host_port:
            return host_port
        if self._resolve_host_port(host_ip, code):
            return self._resolve_host_port(host_ip, code)

        deadline = time.time() + 6.0
        while time.time() < deadline:
            await asyncio.sleep(0.5)
            port = self._resolve_host_port(host_ip, code)
            if port:
                return port

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._scan_for_host_port, host_ip)

    @staticmethod
    def _scan_for_host_port(host_ip: str) -> int:
        """Last resort when UDP discovery is blocked: probe the app's port range."""
        def probe(port: int) -> int | None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                return port if s.connect_ex((host_ip, port)) == 0 else None

        with ThreadPoolExecutor(max_workers=512) as pool:
            for result in pool.map(probe, range(PORT_MIN, PORT_MAX + 1)):
                if result:
                    return result
        return 0

    async def validate_guest(self, request: web.Request) -> web.Response:
        data = await request.json()
        host_ip = str(data.get("host_ip", "")).strip()
        code = str(data.get("code", "")).strip().upper()

        if not validate_ip(host_ip):
            return web.json_response({"status": "error", "message": "Invalid IP"}, status=400)
        if not validate_session_code(code):
            return web.json_response({"status": "error", "message": "Invalid session code"}, status=400)

        port = await self._locate_host(host_ip, code, int(data.get("host_port", 0) or 0))
        if not port:
            return web.json_response(
                {
                    "status": "error",
                    "message": (
                        "PeerCode host not found on this network. Make sure the host "
                        "still has an active session and both devices are on the same Wi-Fi."
                    ),
                },
                status=404,
            )

        try:
            with socket.create_connection((host_ip, port), timeout=5.0):
                pass
        except OSError:
            return web.json_response(
                {
                    "status": "error",
                    "message": (
                        f"Host found at {host_ip}:{port} but refused the connection. "
                        "Allow PeerCode through the firewall on the host device."
                    ),
                },
                status=400,
            )

        return web.json_response({"status": "ok", "port": port})

    async def connect_guest(self, request: web.Request) -> web.Response:
        data = await request.json()
        name = str(data.get("name", "Guest"))
        host_ip = str(data.get("host_ip", "")).strip()
        code = str(data.get("code", "")).strip().upper()
        host_port = int(data.get("host_port", 0) or 0)

        if not validate_ip(host_ip):
            raise GuestConnectionError("Invalid IP")
        if not validate_session_code(code):
            raise GuestConnectionError("Invalid session code")

        host_port = await self._locate_host(host_ip, code, host_port)
        if not host_port:
            raise GuestConnectionError(
                "PeerCode host not found on this network. Make sure the host still has "
                "an active session and both devices are on the same Wi-Fi."
            )

        if self.host or self.guest:
            await self._stop_session()

        self.guest = Guest(name)
        self.guest.on_initial = lambda proj_name: self._schedule(
            {"type": "connected", "project_name": proj_name}
        )
        self.guest.on_sync = lambda path, content, version: self._schedule(
            {"type": "file_update", "path": path, "content": content, "version": version}
        )
        self.guest.on_text_edit = lambda path, op, author: self._schedule(
            {"type": "text_edit", "path": path, "op": op, "author": author}
        )
        self.guest.on_active_file = lambda path, content, version: self._schedule(
            {"type": "active_file", "path": path, "content": content, "version": version}
        )
        self.guest.on_cursor = lambda payload: self._schedule({"type": "cursor_update", **payload})
        self.guest.on_peer_list = lambda peers: self._update_peers(peers)
        self.guest.on_session_closed = lambda message: self._schedule(
            {"type": "session_closed", "message": message}
        )
        self.guest.on_error = lambda message: self._schedule({"type": "error", "message": message})
        self.guest.on_waiting_approval = lambda: self._schedule(
            {"type": "waiting_approval"}
        )

        try:
            self.guest.connect(host_ip, host_port, code)
        except GuestConnectionError:
            self.guest = None
            raise

        return web.json_response({"status": "ok", "session_key": self.guest.session_key, "port": host_port})

    async def approve_guest(self, request: web.Request) -> web.Response:
        data = await request.json()
        request_id = str(data.get("request_id", ""))
        approved = bool(data.get("approve", False))
        if not self.host:
            return web.json_response({"status": "error", "message": "Not hosting"}, status=400)
        if not self.host.resolve_request(request_id, approved):
            return web.json_response({"status": "error", "message": "Unknown or expired request"}, status=404)
        return web.json_response({"status": "ok"})

    async def kick_user(self, request: web.Request) -> web.Response:
        data = await request.json()
        name = str(data.get("name", "")).strip()
        if not name:
            return web.json_response({"status": "error", "message": "Missing user name"}, status=400)
        if not self.host:
            return web.json_response({"status": "error", "message": "Not hosting"}, status=400)
        removed = self.host.kick(name)
        if not removed:
            return web.json_response({"status": "error", "message": f"No guest named '{name}'"}, status=404)
        return web.json_response({"status": "ok", "removed": removed})

    def _resolve_host_port(self, host_ip: str, code: str, host_port: int = 0) -> int:
        if host_port:
            return host_port
        for peer in self.discovered.values():
            if peer.get("ip") == host_ip and str(peer.get("code", "")).upper() == code:
                return int(peer.get("port", 0))
        for peer in self.listener.current_peers():
            if peer.get("ip") == host_ip and str(peer.get("code", "")).upper() == code:
                return int(peer.get("port", 0))
        return 0

    async def session_info(self, request: web.Request) -> web.Response:
        if not self.host:
            return web.json_response({"status": "error", "message": "Not hosting"}, status=400)
        return web.json_response({"status": "ok", **self.host.get_session_info()})

    def _require_guest_ready(self) -> None:
        """Fail fast when the guest session exists but host approval is pending."""
        if self.guest and not self.guest.approved:
            raise GuestConnectionError("Waiting for the host to approve your join request")

    async def project_tree(self, request: web.Request) -> web.Response:
        if self.host:
            tree = self.host.get_project_tree()
        elif self.guest:
            self._require_guest_ready()
            tree = await self.guest.get_project_tree()
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok", "tree": tree})

    async def read_file(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        if self.host:
            res = self.host.read_file(path)
        elif self.guest:
            self._require_guest_ready()
            res = await self.guest.read_file(path)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok", "content": res["content"], "version": res["version"]})

    async def write_file(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        content = str(data["content"])
        version = int(data["version"])
        if self.host:
            res = self.host.save_file(path, content, version)
        elif self.guest:
            self._require_guest_ready()
            res = await self.guest.save_file(path, content, version)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response(res)

    async def set_active_file(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        if self.host:
            self.host.set_active_file(path)
        elif self.guest:
            self._require_guest_ready()
            self.guest.send_active_file(path)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok"})

    async def text_edit(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        op = data.get("op")
        if not isinstance(op, dict):
            raise ValueError("Edit operation must be an object")
        action = str(op.get("op", ""))
        if action not in ("insert", "delete", "replace"):
            raise ValueError("Unsupported edit operation")

        if self.host:
            self.host.apply_text_edit(path, op, self.host.name)
        elif self.guest:
            self.guest.send_text_edit(path, op)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok"})

    async def create_node(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        is_dir = bool(data.get("is_dir", False))
        if self.host:
            self.host.create_node(path, is_dir)
        elif self.guest:
            self._require_guest_ready()
            await self.guest.create_node(path, is_dir)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok"})

    async def rename_node(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        new_name = str(data["new_name"])
        if self.host:
            self.host.rename_node(path, new_name)
        elif self.guest:
            self._require_guest_ready()
            await self.guest.rename_node(path, new_name)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok"})

    async def delete_node(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        if self.host:
            self.host.delete_node(path)
        elif self.guest:
            self._require_guest_ready()
            await self.guest.delete_node(path)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok"})

    async def cursor(self, request: web.Request) -> web.Response:
        data = await request.json()
        path = str(data["path"])
        line = int(data["line"])
        col = int(data["col"])
        color = str(data.get("color", "#7C84FA"))
        if self.host:
            self.host.broadcast_cursor(self.host.name, path, line, col, color)
        elif self.guest:
            self.guest.send_cursor(path, line, col)
        else:
            raise RuntimeError("No active PeerCode session")
        return web.json_response({"status": "ok"})

    async def disconnect(self, request: web.Request) -> web.Response:
        await self._stop_session()
        return web.json_response({"status": "ok"})

    async def peers(self, request: web.Request) -> web.Response:
        return web.json_response({"connected": self.peer_cache, "discovered": list(self.discovered.values())})

    async def ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.flutter_sockets.add(ws)
        await ws.send_str(json.dumps({"type": "discovered", "peers": list(self.discovered.values())}))

        if self.peer_cache:
            await ws.send_str(json.dumps({"type": "peer_list", "peers": self.peer_cache}))

        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    break
        finally:
            self.flutter_sockets.discard(ws)
        return ws

    async def push_to_flutter(self, event: dict[str, Any]) -> None:
        dead: list[web.WebSocketResponse] = []
        data = json.dumps(event)
        for ws in list(self.flutter_sockets):
            try:
                await ws.send_str(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.flutter_sockets.discard(ws)

    def _update_peers(self, peers: list[dict[str, Any]]) -> None:
        self.peer_cache = peers
        self._schedule({"type": "peer_list", "peers": peers})

    async def _stop_session(self) -> None:
        self.peer_cache = []
        if self.host:
            # Detach callbacks first so the dying session cannot leak stale
            # events (session_closed / errors) into a live or starting UI.
            self.host.on_file_change = None
            self.host.on_text_edit = None
            self.host.on_active_file = None
            self.host.on_peer_list = None
            self.host.on_cursor = None
            self.host.on_error = None
            self.host.on_session_closed = None
            self.host.on_join_request = None
            self.host.on_join_resolved = None
            self.host.stop()
            self.host = None
        if self.guest:
            self.guest.on_initial = None
            self.guest.on_sync = None
            self.guest.on_text_edit = None
            self.guest.on_active_file = None
            self.guest.on_cursor = None
            self.guest.on_peer_list = None
            self.guest.on_session_closed = None
            self.guest.on_error = None
            self.guest.on_waiting_approval = None
            self.guest.disconnect()
            self.guest = None

    def _on_discovered(self, peer: dict[str, Any]) -> None:
        self.discovered[str(peer["ip"])] = peer
        self._schedule({"type": "discovered", "peers": list(self.discovered.values())})

    def _on_lost(self, ip: str) -> None:
        self.discovered.pop(ip, None)
        self._schedule({"type": "discovered", "peers": list(self.discovered.values()), "lost": ip})

    def _schedule(self, event: dict[str, Any]) -> None:
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(lambda: self.loop.create_task(self.push_to_flutter(event)))
