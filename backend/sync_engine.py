from __future__ import annotations

import base64
import json
import threading
from collections.abc import Callable


class SyncEngine:
    """Text sync engine using JSON operations (insert/delete/replace).

    Clients send edits as JSON operations:
      {"op": "insert", "index": N, "text": "..."}
      {"op": "delete", "index": N, "length": M}
      {"op": "replace", "index": N, "length": M, "text": "..."}
    """

    def __init__(self, initial_text: str = "") -> None:
        self._text = initial_text
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[str], None]] = []

    def get_text(self) -> str:
        with self._lock:
            return self._text

    def apply_remote_update(self, update_b64: str) -> str:
        """Apply a base64-encoded JSON operation and return the new text."""
        raw = base64.b64decode(update_b64.encode("ascii"))
        with self._lock:
            self._apply_json_operation(raw)
            return self._text

    def local_insert(self, index: int, text: str) -> str:
        """Insert text locally and return the operation as base64."""
        with self._lock:
            self._text = self._text[:index] + text + self._text[index:]
        update_b64 = self._encode_op({"op": "insert", "index": index, "text": text})
        self._notify(update_b64)
        return update_b64

    def local_delete(self, index: int, length: int) -> str:
        """Delete text locally and return the operation as base64."""
        with self._lock:
            self._text = self._text[:index] + self._text[index + length :]
        update_b64 = self._encode_op({"op": "delete", "index": index, "length": length})
        self._notify(update_b64)
        return update_b64

    def get_full_state_b64(self) -> str:
        """Return the full text as a base64-encoded replace operation."""
        with self._lock:
            op = {"op": "replace", "index": 0, "length": len(self._text), "text": self._text}
        return self._encode_op(op)

    def on_update(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def _notify(self, update_b64: str) -> None:
        for callback in list(self._callbacks):
            callback(update_b64)

    def _encode_op(self, op: dict[str, object]) -> str:
        return base64.b64encode(json.dumps(op).encode("utf-8")).decode("ascii")

    def _apply_json_operation(self, raw: bytes) -> None:
        op = json.loads(raw.decode("utf-8"))
        if not isinstance(op, dict):
            raise ValueError("Edit operation must be an object")
        action = str(op.get("op", ""))
        index = int(op.get("index", 0))
        if action == "insert":
            text = str(op.get("text", ""))
            self._text = self._text[:index] + text + self._text[index:]
        elif action == "delete":
            length = int(op.get("length", 0))
            self._text = self._text[:index] + self._text[index + length :]
        elif action == "replace":
            length = int(op.get("length", 0))
            text = str(op.get("text", ""))
            self._text = self._text[:index] + text + self._text[index + length :]
        else:
            raise ValueError(f"Unsupported edit operation: {action}")
