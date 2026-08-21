from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Callable
from typing import Any

DISCOVERY_PORT = 47892
ANNOUNCE_INTERVAL_SECONDS = 2.0
LOST_AFTER_SECONDS = 6.0


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    hostname = socket.gethostname()
    for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
        ip = info[4][0]
        if not ip.startswith("127."):
            return ip
    return "0.0.0.0"


class Broadcaster:
    def __init__(self, name: str, port: int, project_name: str, session_code: str, session_id: str = "") -> None:
        self.name = name
        self.port = port
        self.project_name = project_name
        self.session_code = session_code
        self.session_id = session_id
        self.ip = get_local_ip()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="PeerCodeBroadcaster")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _broadcast_addresses(self) -> list[str]:
        """Global broadcast plus the subnet-directed broadcast, which many
        Wi-Fi routers deliver more reliably than 255.255.255.255."""
        addrs = ["255.255.255.255"]
        parts = self.ip.split(".")
        if len(parts) == 4 and not self.ip.startswith("127.") and self.ip != "0.0.0.0":
            addrs.append(".".join(parts[:3]) + ".255")
        return addrs

    def _run(self) -> None:
        payload = {
            "type": "announce",
            "app": "codeshare",
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "filename": self.project_name,
            "project_name": self.project_name,
            "code": self.session_code,
            "session_id": self.session_id,
        }
        data = json.dumps(payload).encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while not self._stop.is_set():
                for addr in self._broadcast_addresses():
                    try:
                        s.sendto(data, (addr, DISCOVERY_PORT))
                    except OSError:
                        pass
                self._stop.wait(ANNOUNCE_INTERVAL_SECONDS)


class Listener:
    def __init__(
        self,
        on_discovered: Callable[[dict[str, Any]], None],
        on_lost: Callable[[str], None],
    ) -> None:
        self.on_discovered = on_discovered
        self.on_lost = on_lost
        self.local_ip = get_local_ip()
        self.peers: dict[str, dict[str, Any]] = {}
        self.last_seen: dict[str, float] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="PeerCodeListener")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def current_peers(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.peers.values())

    def _run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", DISCOVERY_PORT))
            s.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    data, _ = s.recvfrom(4096)
                    self._handle_packet(data)
                except socket.timeout:
                    pass
                except OSError:
                    pass
                self._expire_lost()

    def _handle_packet(self, data: bytes) -> None:
        try:
            packet = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if packet.get("app") != "codeshare" or packet.get("type") != "announce":
            return
        ip = str(packet.get("ip", ""))
        if not ip or ip == self.local_ip or ip.startswith("127."):
            return
        
        proj_name = str(packet.get("project_name", packet.get("filename", "Untitled")))
        peer = {
            "name": str(packet.get("name", "Unknown")),
            "ip": ip,
            "port": int(packet.get("port", 8765)),
            "filename": proj_name,
            "project_name": proj_name,
            "code": str(packet.get("code", "")),
        }
        with self._lock:
            self.peers[ip] = peer
            self.last_seen[ip] = time.time()
        self.on_discovered(peer)

    def _expire_lost(self) -> None:
        now = time.time()
        lost: list[str] = []
        with self._lock:
            for ip, seen in list(self.last_seen.items()):
                if now - seen > LOST_AFTER_SECONDS:
                    lost.append(ip)
                    self.last_seen.pop(ip, None)
                    self.peers.pop(ip, None)
        for ip in lost:
            self.on_lost(ip)
