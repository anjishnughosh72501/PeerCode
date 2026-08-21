from __future__ import annotations

import asyncio
import base64
import json
import os
import threading
from typing import Any
import websockets
from websockets.server import WebSocketServerProtocol

from discovery import Broadcaster, get_local_ip
from protocol import MSG
from security import SessionInfo, find_available_port, safe_resolve, session_registry
from sync_engine import SyncEngine
from watcher import FileWatcher

PEER_COLORS = [
    "#7C84FA",
    "#36D399",
    "#F97316",
    "#EC4899",
    "#14B8A6",
    "#FACC15",
    "#60A5FA",
    "#C084FC",
]

ALLOWED_MSG_TYPES = {
    MSG.PROJECT_TREE,
    MSG.READ_FILE,
    MSG.SAVE_FILE,
    MSG.CREATE_NODE,
    MSG.RENAME_NODE,
    MSG.DELETE_NODE,
    MSG.CURSOR,
    MSG.TEXT_EDIT,
    MSG.ACTIVE_FILE,
}


class Host:
    def __init__(self, project_path: str, name: str) -> None:
        self.project_path = os.path.realpath(project_path)
        self.name = name
        self.project_name = os.path.basename(self.project_path) or "Project"

        self.ip = get_local_ip()
        self.port = find_available_port()
        self.session: SessionInfo = session_registry.create(self.ip, self.port)
        self.session_code = self.session.code
        self.session_key = self.session.key
        self.session_id = self.session.session_id

        self.opened_files: dict[str, dict[str, Any]] = {}
        self.sync_engines: dict[str, SyncEngine] = {}
        self.active_file: str | None = None

        self.clients: dict[WebSocketServerProtocol, dict[str, Any]] = {}
        self.authenticated: set[WebSocketServerProtocol] = set()

        self.on_file_change = None
        self.on_peer_list = None
        self.on_cursor = None
        self.on_text_edit = None
        self.on_active_file = None
        self.on_error = None
        self.on_session_closed = None

        self._color_index = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: websockets.WebSocketServer | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._closed = False

        self.broadcaster = Broadcaster(
            self.name, self.port, self.project_name, self.session_code, self.session_id
        )
        self.watcher = FileWatcher(self.project_path, self._on_external_file_change)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="PeerCodeHost")
        self._thread.start()
        self._ready.wait(timeout=5.0)
        self.broadcaster.start()
        self.watcher.start()

    def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.broadcaster.stop()
        self.watcher.stop()
        session_registry.remove(self.session_id)
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop).result(timeout=5.0)
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_session_info(self) -> dict[str, Any]:
        return {
            "code": self.session_code,
            "ip": self.ip,
            "port": self.port,
            "session_id": self.session_id,
            "connected_users": [p["name"] for p in self.peer_list()],
        }

    def get_project_tree(self) -> list[dict[str, Any]]:
        tree = []
        ignored_dirs = {
            ".git", ".vs", ".vscode", ".idea", "node_modules",
            ".dart_tool", "build", "__pycache__", "venv", ".venv",
        }
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
            for d in dirs:
                full_path = os.path.join(root, d)
                rel_path = os.path.relpath(full_path, self.project_path).replace("\\", "/")
                tree.append({"path": rel_path, "is_dir": True})
            for f in files:
                if f.startswith("."):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, self.project_path).replace("\\", "/")
                tree.append({"path": rel_path, "is_dir": False})
        tree.sort(key=lambda x: x["path"])
        return tree

    def _get_sync_engine(self, rel_path: str) -> SyncEngine:
        if rel_path not in self.sync_engines:
            content = ""
            if rel_path in self.opened_files:
                content = self.opened_files[rel_path]["content"]
            self.sync_engines[rel_path] = SyncEngine(content)
        return self.sync_engines[rel_path]

    def read_file(self, rel_path: str) -> dict[str, Any]:
        abs_path = safe_resolve(self.project_path, rel_path)
        if os.path.isdir(abs_path):
            raise ValueError("Path is a directory")

        if rel_path in self.opened_files:
            return self.opened_files[rel_path]

        try:
            with open(abs_path, "r", encoding="utf-8", errors="strict") as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError("Binary/unsupported files are not readable in PeerCode")

        mtime = os.path.getmtime(abs_path)
        file_info = {"version": 1, "content": content, "mtime": mtime}
        self.opened_files[rel_path] = file_info
        self.sync_engines[rel_path] = SyncEngine(content)
        self.watcher.track_file(rel_path)
        return file_info

    def set_active_file(self, rel_path: str) -> dict[str, Any]:
        file_info = self.read_file(rel_path)
        self.active_file = rel_path
        payload = {
            "path": rel_path,
            "content": file_info["content"],
            "version": file_info["version"],
        }
        self._broadcast(MSG(MSG.ACTIVE_FILE, payload))
        if self.on_active_file:
            self.on_active_file(rel_path, file_info["content"], file_info["version"])
        return payload

    def apply_text_edit(self, rel_path: str, op: dict[str, Any], author: str = "") -> str:
        if rel_path not in self.opened_files:
            self.read_file(rel_path)

        engine = self._get_sync_engine(rel_path)
        raw = json.dumps(op).encode("utf-8")
        update_b64 = base64.b64encode(raw).decode("ascii")
        new_text = engine.apply_remote_update(update_b64)

        file_info = self.opened_files[rel_path]
        file_info["content"] = new_text
        self.opened_files[rel_path] = file_info

        payload = {"path": rel_path, "op": op, "author": author}
        self._broadcast(MSG(MSG.TEXT_EDIT, payload))
        if self.on_text_edit:
            self.on_text_edit(rel_path, op, author)
        return new_text

    def save_file(self, rel_path: str, content: str, client_version: int) -> dict[str, Any]:
        abs_path = safe_resolve(self.project_path, rel_path)

        if rel_path not in self.opened_files:
            if os.path.exists(abs_path):
                self.read_file(rel_path)
            else:
                self.opened_files[rel_path] = {"version": 0, "content": "", "mtime": 0.0}
                self.sync_engines[rel_path] = SyncEngine("")
                self.watcher.track_file(rel_path)

        file_info = self.opened_files[rel_path]
        server_version = file_info["version"]

        if client_version != server_version:
            return {
                "status": "conflict",
                "server_version": server_version,
                "content_on_server": file_info["content"],
            }

        self.watcher.ignore_file(rel_path)
        try:
            with open(abs_path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            mtime = os.path.getmtime(abs_path)
        finally:
            self.watcher.resume_file(rel_path)

        new_version = server_version + 1
        self.opened_files[rel_path] = {"version": new_version, "content": content, "mtime": mtime}
        self.sync_engines[rel_path] = SyncEngine(content)

        self._broadcast(MSG(MSG.FILE_UPDATE, {"path": rel_path, "content": content, "version": new_version}))
        if self.on_file_change:
            self.on_file_change(rel_path, content, new_version)

        return {"status": "ok", "version": new_version}

    def create_node(self, rel_path: str, is_dir: bool) -> None:
        abs_path = safe_resolve(self.project_path, rel_path)
        if is_dir:
            os.makedirs(abs_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write("")
        self._broadcast(MSG(MSG.PROJECT_TREE, {"tree": self.get_project_tree()}))

    def rename_node(self, rel_path: str, new_name: str) -> None:
        abs_path = safe_resolve(self.project_path, rel_path)
        new_abs_path = safe_resolve(self.project_path, os.path.join(os.path.dirname(rel_path), new_name))
        os.rename(abs_path, new_abs_path)

        old_prefix = rel_path
        new_prefix = os.path.join(os.path.dirname(rel_path), new_name).replace("\\", "/")

        to_rename = []
        for path in list(self.opened_files.keys()):
            if path == old_prefix:
                to_rename.append((path, new_prefix))
            elif path.startswith(old_prefix + "/"):
                new_path = path.replace(old_prefix + "/", new_prefix + "/")
                to_rename.append((path, new_path))

        for old_p, new_p in to_rename:
            self.watcher.untrack_file(old_p)
            file_info = self.opened_files.pop(old_p)
            self.opened_files[new_p] = file_info
            if old_p in self.sync_engines:
                self.sync_engines[new_p] = self.sync_engines.pop(old_p)
            self.watcher.track_file(new_p)

        if self.active_file == old_prefix:
            self.active_file = new_prefix

        self._broadcast(MSG(MSG.PROJECT_TREE, {"tree": self.get_project_tree()}))

    def delete_node(self, rel_path: str) -> None:
        abs_path = safe_resolve(self.project_path, rel_path)
        if os.path.isdir(abs_path):
            import shutil
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)

        old_prefix = rel_path
        to_delete = []
        for path in list(self.opened_files.keys()):
            if path == old_prefix or path.startswith(old_prefix + "/"):
                to_delete.append(path)

        for p in to_delete:
            self.watcher.untrack_file(p)
            self.opened_files.pop(p, None)
            self.sync_engines.pop(p, None)

        if self.active_file and (self.active_file == old_prefix or self.active_file.startswith(old_prefix + "/")):
            self.active_file = None

        self._broadcast(MSG(MSG.PROJECT_TREE, {"tree": self.get_project_tree()}))

    def broadcast_cursor(self, author: str, path: str, line: int, col: int, color: str) -> None:
        payload = {"author": author, "path": path, "line": line, "col": col, "color": color}
        self._broadcast(MSG(MSG.CURSOR, payload))
        if self.on_cursor:
            self.on_cursor(payload)

    def peer_list(self) -> list[dict[str, Any]]:
        host_peer = {"name": self.name, "color": "#7C84FA", "isHost": True}
        return [host_peer] + list(self.clients.values())

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_server())
        self._ready.set()
        self._loop.run_forever()

    async def _start_server(self) -> None:
        self._server = await websockets.serve(self._handler, "0.0.0.0", self.port)

    async def _shutdown(self) -> None:
        close_msg = MSG(MSG.SESSION_CLOSED, {"message": "Host ended the session"}).to_json()
        for websocket in list(self.clients):
            try:
                await websocket.send(close_msg)
                await websocket.close()
            except Exception:
                pass
        if self.on_session_closed:
            self.on_session_closed()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            msg = MSG.from_json(str(raw))
            if msg.type != MSG.HANDSHAKE:
                await websocket.close(1008, "Unauthorized")
                return

            code = str(msg.payload.get("code", "")).upper()
            key = str(msg.payload.get("key", ""))
            peer_name = str(msg.payload.get("name", "Guest"))

            session = session_registry.get_by_code(code)
            if not session or session.session_id != self.session_id:
                await websocket.send(MSG(MSG.ERROR, {"message": "Wrong code"}).to_json())
                await websocket.close(1008, "Wrong code")
                return

            if key:
                if not session_registry.validate_key(code, key):
                    await websocket.send(MSG(MSG.ERROR, {"message": "Invalid session key"}).to_json())
                    await websocket.close(1008, "Unauthorized")
                    return
            else:
                key = session.key

            color = PEER_COLORS[self._color_index % len(PEER_COLORS)]
            self._color_index += 1

            self.clients[websocket] = {"name": peer_name, "color": color, "isHost": False, "key": key}
            self.authenticated.add(websocket)

            init_payload: dict[str, Any] = {
                "project_name": self.project_name,
                "color": color,
                "session_key": key,
                "session_id": self.session_id,
            }
            if self.active_file and self.active_file in self.opened_files:
                info = self.opened_files[self.active_file]
                init_payload["active_file"] = {
                    "path": self.active_file,
                    "content": info["content"],
                    "version": info["version"],
                }

            await websocket.send(MSG(MSG.INIT, init_payload).to_json())
            await self._broadcast_peer_list()

            async for incoming in websocket:
                await self._handle_message(websocket, MSG.from_json(str(incoming)))
        except asyncio.TimeoutError:
            pass
        except Exception as exc:
            self._emit_error(str(exc))
        finally:
            self.clients.pop(websocket, None)
            self.authenticated.discard(websocket)
            await self._broadcast_peer_list()

    def _validate_client(self, websocket: WebSocketServerProtocol, msg: MSG) -> bool:
        if websocket not in self.authenticated:
            return False
        client = self.clients.get(websocket)
        if not client:
            return False
        key = str(msg.payload.get("session_key", ""))
        if key and not session_registry.validate_key(self.session_code, key):
            return False
        return msg.type in ALLOWED_MSG_TYPES

    async def _handle_message(self, websocket: WebSocketServerProtocol, msg: MSG) -> None:
        if not self._validate_client(websocket, msg):
            return

        peer = self.clients.get(websocket, {"name": "Guest", "color": "#7C84FA"})
        try:
            if msg.type == MSG.PROJECT_TREE:
                tree = self.get_project_tree()
                await websocket.send(MSG(MSG.PROJECT_TREE, {"tree": tree}, id=msg.id).to_json())

            elif msg.type == MSG.READ_FILE:
                path = str(msg.payload.get("path", ""))
                file_info = self.read_file(path)
                await websocket.send(
                    MSG(
                        MSG.READ_FILE,
                        {"path": path, "content": file_info["content"], "version": file_info["version"]},
                        id=msg.id,
                    ).to_json()
                )

            elif msg.type == MSG.SAVE_FILE:
                path = str(msg.payload.get("path", ""))
                content = str(msg.payload.get("content", ""))
                version = int(msg.payload.get("version", 0))
                res = self.save_file(path, content, version)
                await websocket.send(MSG(MSG.SAVE_FILE, res, id=msg.id).to_json())

            elif msg.type == MSG.TEXT_EDIT:
                path = str(msg.payload.get("path", ""))
                op = msg.payload.get("op")
                if isinstance(op, dict):
                    self.apply_text_edit(path, op, peer["name"])

            elif msg.type == MSG.ACTIVE_FILE:
                path = str(msg.payload.get("path", ""))
                if path:
                    self.set_active_file(path)

            elif msg.type == MSG.CREATE_NODE:
                path = str(msg.payload.get("path", ""))
                is_dir = bool(msg.payload.get("is_dir", False))
                self.create_node(path, is_dir)
                await websocket.send(MSG(MSG.CREATE_NODE, {"status": "ok"}, id=msg.id).to_json())

            elif msg.type == MSG.RENAME_NODE:
                path = str(msg.payload.get("path", ""))
                new_name = str(msg.payload.get("new_name", ""))
                self.rename_node(path, new_name)
                await websocket.send(MSG(MSG.RENAME_NODE, {"status": "ok"}, id=msg.id).to_json())

            elif msg.type == MSG.DELETE_NODE:
                path = str(msg.payload.get("path", ""))
                self.delete_node(path)
                await websocket.send(MSG(MSG.DELETE_NODE, {"status": "ok"}, id=msg.id).to_json())

            elif msg.type == MSG.CURSOR:
                path = str(msg.payload.get("path", ""))
                line = int(msg.payload.get("line", 0))
                col = int(msg.payload.get("col", 0))
                await self._broadcast_async(
                    MSG(
                        MSG.CURSOR,
                        {"author": peer["name"], "path": path, "line": line, "col": col, "color": peer["color"]},
                    ),
                    exclude=websocket,
                )
                if self.on_cursor:
                    self.on_cursor({"author": peer["name"], "path": path, "line": line, "col": col, "color": peer["color"]})
        except Exception as exc:
            await websocket.send(MSG(MSG.ERROR, {"message": str(exc)}, id=msg.id).to_json())
            self._emit_error(f"Error handling peer request: {exc}")

    def _on_external_file_change(self, rel_path: str, content: str) -> None:
        if rel_path not in self.opened_files:
            return

        file_info = self.opened_files[rel_path]
        new_version = file_info["version"] + 1
        self.opened_files[rel_path] = {
            "version": new_version,
            "content": content,
            "mtime": os.path.getmtime(safe_resolve(self.project_path, rel_path)),
        }
        self.sync_engines[rel_path] = SyncEngine(content)
        self._broadcast(MSG(MSG.FILE_UPDATE, {"path": rel_path, "content": content, "version": new_version}))
        if self.on_file_change:
            self.on_file_change(rel_path, content, new_version)

    async def _broadcast_peer_list(self) -> None:
        peers = self.peer_list()
        msg = MSG(MSG.PEER_LIST, {"peers": peers})
        await self._broadcast_async(msg)
        if self.on_peer_list:
            self.on_peer_list(peers)

    def _broadcast(self, msg: MSG) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._broadcast_async(msg), self._loop)

    async def _broadcast_async(self, msg: MSG, exclude: WebSocketServerProtocol | None = None) -> None:
        data = msg.to_json()
        for websocket in list(self.clients):
            if websocket is exclude or websocket not in self.authenticated:
                continue
            try:
                await websocket.send(data)
            except Exception as exc:
                self._emit_error(str(exc))

    def _emit_error(self, message: str) -> None:
        if self.on_error:
            self.on_error(message)
