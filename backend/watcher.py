from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable


class FileWatcher:
    def __init__(self, root_dir: str, on_change: Callable[[str, str], None]) -> None:
        self.root_dir = os.path.realpath(root_dir)
        self.on_change = on_change
        self.tracked_files: set[str] = set()
        self.ignored_files: set[str] = set()

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._observer = None

        self._mtimes: dict[str, float] = {}
        self._contents: dict[str, str] = {}

    def track_file(self, rel_path: str) -> None:
        with self._lock:
            self.tracked_files.add(rel_path)
            abs_path = os.path.join(self.root_dir, rel_path)
            if os.path.exists(abs_path):
                self._mtimes[rel_path] = os.path.getmtime(abs_path)
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        self._contents[rel_path] = f.read()
                except Exception:
                    pass

    def untrack_file(self, rel_path: str) -> None:
        with self._lock:
            self.tracked_files.discard(rel_path)
            self._mtimes.pop(rel_path, None)
            self._contents.pop(rel_path, None)

    def ignore_file(self, rel_path: str) -> None:
        """Temporarily ignore modifications from a file (e.g. while server writes it)."""
        with self._lock:
            self.ignored_files.add(rel_path)

    def resume_file(self, rel_path: str) -> None:
        """Resume tracking after server-initiated write, updating local cached mtime/content."""
        with self._lock:
            abs_path = os.path.join(self.root_dir, rel_path)
            if os.path.exists(abs_path):
                self._mtimes[rel_path] = os.path.getmtime(abs_path)
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                        self._contents[rel_path] = f.read()
                except Exception:
                    pass
            self.ignored_files.discard(rel_path)

    def start(self) -> None:
        self._stop_event.clear()
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            watcher_self = self

            class WatchdogHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    if event.is_directory:
                        return
                    abs_path = os.path.realpath(event.src_path)
                    if not abs_path.startswith(watcher_self.root_dir):
                        return
                    rel_path = os.path.relpath(abs_path, watcher_self.root_dir).replace("\\", "/")

                    with watcher_self._lock:
                        if rel_path not in watcher_self.tracked_files:
                            return
                        if rel_path in watcher_self.ignored_files:
                            return

                    # Wait brief moment to let editors flush write
                    time.sleep(0.05)
                    watcher_self._check_file(rel_path)

            self._observer = Observer()
            self._observer.schedule(WatchdogHandler(), self.root_dir, recursive=True)
            self._observer.start()
            print("Started FileWatcher using watchdog observer.")
        except Exception as e:
            print(f"Could not use watchdog observer ({e}). Falling back to manual polling.")
            self._observer = None

        if self._observer is None:
            self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="PeerCodeWatcher")
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(1.5)
            with self._lock:
                files_to_check = list(self.tracked_files)

            for rel_path in files_to_check:
                with self._lock:
                    if rel_path in self.ignored_files:
                        continue
                self._check_file(rel_path)

    def _check_file(self, rel_path: str) -> None:
        abs_path = os.path.join(self.root_dir, rel_path)
        if not os.path.exists(abs_path):
            return

        try:
            mtime = os.path.getmtime(abs_path)
            with self._lock:
                old_mtime = self._mtimes.get(rel_path, 0.0)

            if mtime != old_mtime:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                with self._lock:
                    old_content = self._contents.get(rel_path, "")
                    self._mtimes[rel_path] = mtime
                    self._contents[rel_path] = content

                if content != old_content:
                    print(f"External file change detected: {rel_path}")
                    self.on_change(rel_path, content)
        except Exception as e:
            print(f"Error checking file {rel_path}: {e}")
