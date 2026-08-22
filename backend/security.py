from __future__ import annotations

import os
import random
import secrets
import socket
import threading

# Session codes: uppercase letters + digits, excluding O 0 I 1 L
SESSION_CODE_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
SESSION_CODE_LENGTH = 6
PORT_MIN = 45000
PORT_MAX = 45199


def generate_session_code(used: set[str] | None = None) -> str:
    """Generate a unique 6-character session code."""
    taken = used or set()
    for _ in range(1000):
        code = "".join(secrets.choice(SESSION_CODE_CHARS) for _ in range(SESSION_CODE_LENGTH))
        if code not in taken:
            return code
    raise RuntimeError("Unable to generate a unique session code")


def generate_session_id() -> str:
    return secrets.token_hex(16)


def generate_session_key() -> str:
    """Return a 256-bit session key as hex."""
    return secrets.token_hex(32)


def validate_ip(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def validate_session_code(code: str) -> bool:
    if len(code) != SESSION_CODE_LENGTH:
        return False
    return all(c in SESSION_CODE_CHARS for c in code.upper())


def find_available_port(min_port: int = PORT_MIN, max_port: int = PORT_MAX) -> int:
    """Pick a random available port in the LAN range."""
    ports = list(range(min_port, max_port + 1))
    random.shuffle(ports)
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available port in range {min_port}-{max_port}")


def safe_resolve(root_dir: str, client_path: str) -> str:
    """Resolves client path relative to project root, enforcing path safety."""
    real_root = os.path.realpath(root_dir)
    clean_path = client_path.replace("\\", "/").strip().lstrip("/")
    joined = os.path.join(real_root, clean_path)
    real_joined = os.path.realpath(joined)

    prefix = real_root if real_root.endswith(os.sep) else real_root + os.sep
    if real_joined != real_root and not real_joined.startswith(prefix):
        raise PermissionError("Access denied: path is outside the project root")

    return real_joined


class SessionInfo:
    __slots__ = ("session_id", "code", "key", "port", "host_ip")

    def __init__(self, session_id: str, code: str, key: str, port: int, host_ip: str) -> None:
        self.session_id = session_id
        self.code = code
        self.key = key
        self.port = port
        self.host_ip = host_ip


class SessionRegistry:
    """In-memory store for active hosted sessions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, SessionInfo] = {}
        self._by_code: dict[str, str] = {}

    def create(self, host_ip: str, port: int) -> SessionInfo:
        with self._lock:
            used = set(self._by_code.keys())
            code = generate_session_code(used)
            session_id = generate_session_id()
            key = generate_session_key()
            info = SessionInfo(session_id, code, key, port, host_ip)
            self._by_id[session_id] = info
            self._by_code[code] = session_id
            return info

    def get_by_code(self, code: str) -> SessionInfo | None:
        with self._lock:
            session_id = self._by_code.get(code.upper())
            if not session_id:
                return None
            return self._by_id.get(session_id)

    def validate_key(self, code: str, key: str) -> bool:
        info = self.get_by_code(code)
        if not info:
            return False
        return secrets.compare_digest(info.key, key)

    def remove(self, session_id: str) -> None:
        with self._lock:
            info = self._by_id.pop(session_id, None)
            if info:
                self._by_code.pop(info.code, None)


# Global in-memory session registry
session_registry = SessionRegistry()
