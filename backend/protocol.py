from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass(frozen=True)
class MSG:
    INIT: ClassVar[str] = "init"
    HANDSHAKE: ClassVar[str] = "handshake"
    PEER_LIST: ClassVar[str] = "peer_list"
    PROJECT_TREE: ClassVar[str] = "project_tree"
    READ_FILE: ClassVar[str] = "read_file"
    SAVE_FILE: ClassVar[str] = "save_file"
    CREATE_NODE: ClassVar[str] = "create_node"
    RENAME_NODE: ClassVar[str] = "rename_node"
    DELETE_NODE: ClassVar[str] = "delete_node"
    CURSOR: ClassVar[str] = "cursor"
    FILE_UPDATE: ClassVar[str] = "file_update"
    TEXT_EDIT: ClassVar[str] = "text_edit"
    ACTIVE_FILE: ClassVar[str] = "active_file"
    SESSION_CLOSED: ClassVar[str] = "session_closed"
    ERROR: ClassVar[str] = "error"

    type: str
    payload: dict[str, Any]
    id: str | None = None

    def to_json(self) -> str:
        return json.dumps({"type": self.type, "payload": self.payload, "id": self.id})

    @classmethod
    def from_json(cls, s: str) -> "MSG":
        data = json.loads(s)
        msg_type = data.get("type")
        payload = data.get("payload", {})
        msg_id = data.get("id")
        if not isinstance(msg_type, str):
            raise ValueError("Message type must be a string")
        if not isinstance(payload, dict):
            raise ValueError("Message payload must be an object")
        return cls(type=msg_type, payload=payload, id=msg_id)
