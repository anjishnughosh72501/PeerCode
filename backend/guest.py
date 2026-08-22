from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import Callable
from typing import Any
import websockets
from websockets.client import WebSocketClientProtocol

from protocol import MSG


class GuestConnectionError(Exception):
    """Raised when guest cannot join a session."""


class Guest:
    def __init__(self, name: str) -> None:
        self.name = name
        self.websocket: WebSocketClientProtocol | None = None
        self.session_key: str = ""
        self.session_id: str = ""
        self.approved: bool = False
        self._pending_requests: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._connect_error: str | None = None

        self.on_initial: Callable[[str], None] | None = None
        self.on_sync: Callable[[str, str, int], None] | None = None
        self.on_text_edit: Callable[[str, dict[str, Any], str], None] | None = None
        self.on_active_file: Callable[[str, str, int], None] | None = None
        self.on_cursor: Callable[[dict[str, Any]], None] | None = None
        self.on_peer_list: Callable[[list[dict[str, Any]]], None] | None = None
        self.on_session_closed: Callable[[str], None] | None = None
        self.on_error: Callable[[str], None] | None = None
        self.on_waiting_approval: Callable[[], None] | None = None

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def connect(self, host_ip: str, port: int, code: str) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._connect_error = None
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(host_ip, port, code.upper()),
            daemon=True,
            name="PeerCodeGuest",
        )
        self._thread.start()
        if not self._ready.wait(timeout=10.0):
            raise GuestConnectionError("Could not reach the host. Allow PeerCode through the firewall on the host device.")
        if self._connect_error:
            raise GuestConnectionError(self._connect_error)

    def call(self, coro, timeout: float = 15.0) -> Any:
        """Run a coroutine on the guest event loop from a foreign thread (blocking)."""
        if not self._loop:
            raise RuntimeError("Guest is not connected")
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=timeout)

    def disconnect(self) -> None:
        # Schedule the close on the guest loop without blocking the calling
        # loop (which may be the aiohttp bridge loop) with .result().
        if self._loop and self.websocket and self._loop.is_running():
            websocket = self.websocket
            loop = self._loop

            def _close_then_stop() -> None:
                async def _closer() -> None:
                    try:
                        await asyncio.wait_for(websocket.close(), timeout=1.5)
                    except Exception:
                        pass
                    loop.stop()

                loop.create_task(_closer())

            try:
                self._loop.call_soon_threadsafe(_close_then_stop)
            except RuntimeError:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)

    async def _send_request(self, msg_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Request/response round trip.

        May be awaited from ANY event loop (e.g. the aiohttp bridge loop).
        The reply future is created on the caller's loop and resolved from the
        guest receive loop via call_soon_threadsafe; the websocket send is
        always scheduled on the guest loop that owns the connection.
        """
        if not self.websocket or not self._loop:
            raise RuntimeError("Guest is not connected to any session")

        req_id = str(uuid.uuid4())
        fut: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()

        def register() -> None:
            self._pending_requests[req_id] = fut

        self._loop.call_soon_threadsafe(register)

        payload = dict(payload)
        if self.session_key:
            payload["session_key"] = self.session_key

        msg = MSG(msg_type, payload, id=req_id)
        try:
            send_fut = asyncio.run_coroutine_threadsafe(self.websocket.send(msg.to_json()), self._loop)
            await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(send_fut)), timeout=5.0)
        except Exception as exc:
            self._pending_requests.pop(req_id, None)
            raise RuntimeError("Could not send the request to the host") from exc

        try:
            result = await asyncio.wait_for(fut, timeout=10.0)
            if "message" in result and msg_type != MSG.ERROR:
                raise RuntimeError(result["message"])
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise TimeoutError(f"Request {msg_type} timed out waiting for host response")

    async def get_project_tree(self) -> list[dict[str, Any]]:
        res = await self._send_request(MSG.PROJECT_TREE, {})
        return res.get("tree", [])

    async def read_file(self, path: str) -> dict[str, Any]:
        return await self._send_request(MSG.READ_FILE, {"path": path})

    async def save_file(self, path: str, content: str, version: int) -> dict[str, Any]:
        return await self._send_request(MSG.SAVE_FILE, {"path": path, "content": content, "version": version})

    async def create_node(self, path: str, is_dir: bool) -> dict[str, Any]:
        return await self._send_request(MSG.CREATE_NODE, {"path": path, "is_dir": is_dir})

    async def rename_node(self, path: str, new_name: str) -> dict[str, Any]:
        return await self._send_request(MSG.RENAME_NODE, {"path": path, "new_name": new_name})

    async def delete_node(self, path: str) -> dict[str, Any]:
        return await self._send_request(MSG.DELETE_NODE, {"path": path})

    def send_cursor(self, path: str, line: int, col: int) -> None:
        if self.websocket and self._loop:
            payload: dict[str, Any] = {"path": path, "line": line, "col": col}
            if self.session_key:
                payload["session_key"] = self.session_key
            msg = MSG(MSG.CURSOR, payload)
            asyncio.run_coroutine_threadsafe(self.websocket.send(msg.to_json()), self._loop)

    def send_text_edit(self, path: str, op: dict[str, Any]) -> None:
        if self.websocket and self._loop:
            payload: dict[str, Any] = {"path": path, "op": op}
            if self.session_key:
                payload["session_key"] = self.session_key
            msg = MSG(MSG.TEXT_EDIT, payload)
            asyncio.run_coroutine_threadsafe(self.websocket.send(msg.to_json()), self._loop)

    def send_active_file(self, path: str) -> None:
        if self.websocket and self._loop:
            payload: dict[str, Any] = {"path": path}
            if self.session_key:
                payload["session_key"] = self.session_key
            msg = MSG(MSG.ACTIVE_FILE, payload)
            asyncio.run_coroutine_threadsafe(self.websocket.send(msg.to_json()), self._loop)

    def _run_loop(self, host_ip: str, port: int, code: str) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_receive(host_ip, port, code))

    async def _connect_and_receive(self, host_ip: str, port: int, code: str) -> None:
        try:
            websocket = None
            for attempt in range(3):
                try:
                    websocket = await asyncio.wait_for(
                        websockets.connect(f"ws://{host_ip}:{port}"),
                        timeout=5.0,
                    )
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.8)
            self.websocket = websocket
            await self.websocket.send(
                MSG(MSG.HANDSHAKE, {"code": code, "name": self.name, "key": ""}).to_json()
            )

            init_msg: MSG | None = None
            while init_msg is None:
                raw = await asyncio.wait_for(self.websocket.recv(), timeout=150.0)
                msg = MSG.from_json(str(raw))
                if msg.type == MSG.JOIN_PENDING:
                    if self.on_waiting_approval:
                        self.on_waiting_approval()
                    self._ready.set()
                    continue
                if msg.type == MSG.ERROR:
                    message = str(msg.payload.get("message", "Connection rejected"))
                    if self._ready.is_set():
                        self._emit_error(message)
                    else:
                        self._connect_error = message
                        self._ready.set()
                    return

                if msg.type != MSG.INIT:
                    message = "Invalid host response"
                    if self._ready.is_set():
                        self._emit_error(message)
                    else:
                        self._connect_error = message
                        self._ready.set()
                    return
                init_msg = msg

            self.session_key = str(init_msg.payload.get("session_key", ""))
            self.session_id = str(init_msg.payload.get("session_id", ""))
            self.approved = True
            project_name = str(init_msg.payload.get("project_name", "Remote Project"))

            active = init_msg.payload.get("active_file")
            if isinstance(active, dict) and self.on_active_file:
                path = str(active.get("path", ""))
                content = str(active.get("content", ""))
                version = int(active.get("version", 1))
                if path:
                    self.on_active_file(path, content, version)

            self._ready.set()
            if self.on_initial:
                self.on_initial(project_name)

            await self._receive_loop()
        except asyncio.TimeoutError:
            self._connect_error = "Host unavailable"
            self._ready.set()
        except Exception as exc:
            self._connect_error = str(exc) or "Host unavailable"
            self._ready.set()

    async def _receive_loop(self) -> None:
        assert self.websocket is not None
        try:
            async for raw in self.websocket:
                msg = MSG.from_json(str(raw))

                if msg.id and msg.id in self._pending_requests:
                    fut = self._pending_requests.pop(msg.id)
                    if not fut.done():
                        fut.get_loop().call_soon_threadsafe(fut.set_result, msg.payload)
                    continue

                if msg.type == MSG.FILE_UPDATE:
                    path = str(msg.payload.get("path", ""))
                    content = str(msg.payload.get("content", ""))
                    version = int(msg.payload.get("version", 0))
                    if self.on_sync:
                        self.on_sync(path, content, version)

                elif msg.type == MSG.TEXT_EDIT and self.on_text_edit:
                    path = str(msg.payload.get("path", ""))
                    op = msg.payload.get("op")
                    author = str(msg.payload.get("author", ""))
                    if isinstance(op, dict):
                        self.on_text_edit(path, op, author)

                elif msg.type == MSG.ACTIVE_FILE and self.on_active_file:
                    path = str(msg.payload.get("path", ""))
                    content = str(msg.payload.get("content", ""))
                    version = int(msg.payload.get("version", 1))
                    self.on_active_file(path, content, version)

                elif msg.type == MSG.CURSOR and self.on_cursor:
                    self.on_cursor(msg.payload)

                elif msg.type == MSG.PEER_LIST and self.on_peer_list:
                    peers = msg.payload.get("peers", [])
                    if isinstance(peers, list):
                        self.on_peer_list(peers)

                elif msg.type == MSG.SESSION_CLOSED:
                    message = str(msg.payload.get("message", "Session closed"))
                    if self.on_session_closed:
                        self.on_session_closed(message)
                    break

                elif msg.type == MSG.KICK:
                    message = str(msg.payload.get("message", "The host removed you from the session"))
                    if self.on_session_closed:
                        self.on_session_closed(message)
                    break

                elif msg.type == MSG.ERROR:
                    self._emit_error(str(msg.payload.get("message", "Unknown error")))
        except Exception as exc:
            self._emit_error(str(exc))

    def _emit_error(self, message: str) -> None:
        if self.on_error:
            self.on_error(message)
