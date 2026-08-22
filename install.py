#!/usr/bin/env python3
"""PeerCode universal installer - one file, any OS.

Copy THIS file alone onto any computer (Windows, macOS or Linux) and run:

    python install.py          # Windows
    python3 install.py         # macOS / Linux

What it does:
  1. Verifies Python 3.9+
  2. Downloads the PeerCode source (skipped if you are already inside the repo)
  3. Creates an isolated virtual environment (.venv)
  4. Installs every backend dependency
  5. Rebuilds the web UI when Node.js is available (uses the bundled build otherwise)
  6. Starts PeerCode

Options:
  --no-run     Install everything but do not launch
  --dir PATH   Where to place the source when bootstrapping (default: ./PeerCode)
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/anjishnughosh72501/PeerCode.git"
ZIP_URL = "https://github.com/anjishnughosh72501/PeerCode/archive/refs/heads/main.zip"


def step(message: str) -> None:
    print(f"\n[PeerCode] {message}")


def fail(message: str, hint: str = "") -> None:
    print(f"\nERROR: {message}")
    if hint:
        print(hint)
    sys.exit(1)


def venv_python(venv_dir: Path) -> Path:
    sub = "Scripts" if os.name == "nt" else "bin"
    name = "python.exe" if os.name == "nt" else ("python3" if Path(venv_dir / "bin" / "python3").exists() else "python")
    return venv_dir / sub / name


def bootstrap_source(root: Path, target_name: str) -> Path:
    """Download the source when install.py is run outside of a checkout."""
    target = root / target_name
    if (target / "app.py").exists():
        return target

    step("Fetching PeerCode source...")
    if shutil.which("git"):
        result = subprocess.run(
            ["git", "clone", "--depth", "1", REPO_URL, str(target)],
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return target
        print("git clone failed - falling back to ZIP download.")

    zip_path = root / "peercode-main.zip"
    try:
        with urllib.request.urlopen(ZIP_URL, timeout=60) as resp, open(zip_path, "wb") as fh:
            fh.write(resp.read())
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(root)
        zip_path.unlink(missing_ok=True)
        extracted = next(root.glob("PeerCode-main"))
        extracted.rename(target)
        return target
    except Exception as exc:
        raise SystemExit(
            "Could not download the source automatically.\n"
            f"Reason: {exc}\n\n"
            f"Please download the repository manually from {REPO_URL}\n"
            "(green Code button -> Download ZIP), extract it, and run this\n"
            "installer again from inside the extracted folder."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Install and launch PeerCode.")
    parser.add_argument("--no-run", action="store_true", help="install without launching")
    parser.add_argument("--dir", default="PeerCode", help="target folder when downloading the source")
    args = parser.parse_args()

    print("=" * 48)
    print("  PeerCode installer - Windows / macOS / Linux")
    print("=" * 48)

    if sys.version_info < (3, 9):
        fail(
            f"Python 3.9+ is required (you are running {platform.python_version()}).",
            "Get it from https://www.python.org/downloads/",
        )
    step(f"Python {platform.python_version()} detected on {platform.system()}.")

    here = Path(__file__).resolve().parent
    if (here / "app.py").exists():
        root = here
    else:
        try:
            root = bootstrap_source(here, args.dir)
        except SystemExit:
            raise
        except Exception as exc:
            fail(str(exc))
        step(f"Source ready at {root}")

    step("Creating an isolated environment (.venv)...")
    venv_dir = root / ".venv"
    created = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)])
    if created.returncode != 0:
        fail(
            "Could not create a virtual environment.",
            "On Debian/Ubuntu install it with:  sudo apt install python3-venv",
        )
    vpy = venv_python(venv_dir)
    if not vpy.exists():
        fail("Virtual environment python not found.", "Delete the .venv folder and re-run.")

    step("Installing dependencies (websockets, aiohttp, watchdog)...")
    pip_cmd = [str(vpy), "-m", "pip"]
    subprocess.run(pip_cmd + ["install", "--upgrade", "pip", "--quiet"], check=True)
    res = subprocess.run(pip_cmd + ["install", "-r", str(root / "backend" / "requirements.txt")])
    if res.returncode != 0:
        fail("Dependency installation failed. Check your internet connection and re-run.")
    native = subprocess.run(
        pip_cmd + ["install", "pywebview", "--quiet"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if native.returncode != 0:
        print("[PeerCode] pywebview unavailable - the UI will open in your browser instead.")

    step("Preparing the web UI...")
    npm = shutil.which("npm")
    if npm:
        res = subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=root / "webapp")
        if res.returncode == 0:
            res = subprocess.run([npm, "run", "build"], cwd=root / "webapp")
        if res.returncode != 0:
            print("[PeerCode] Web build failed - using the prebuilt bundle in web/.")
        else:
            print("[PeerCode] Web UI built successfully.")
    else:
        print("Node.js not found - using the prebuilt web bundle shipped in the repo.")

    print("\n" + "=" * 48)
    if args.no_run:
        print("  Installation complete!")
        print(f"  Start PeerCode later from '{root.name}' with:")
        print(f"    {'python' if os.name != 'nt' else 'python'} app.py  (inside the .venv)")
    else:
        print("  Starting PeerCode...")
        print("  The UI opens at http://127.0.0.1:7432/")
    print("=" * 48 + "\n")

    if not args.no_run:
        try:
            os.chdir(root)
            sys.exit(subprocess.call([str(vpy), "app.py"]))
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[PeerCode] Cancelled.")
