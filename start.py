#!/usr/bin/env python3
"""
Premier League Model Engine & Dashboard Launcher
Starts FastAPI backend server and Vite frontend concurrently.
Gracefully shuts down both processes on Ctrl+C.

A previous run of this project that still holds port 8000 or 5173 is stopped first. A foreign
process on those ports is never killed unless you pass ``--force``.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_DIR / "frontend"


def listeners(port: int) -> list[tuple[int, str]]:
    """(pid, command line) of the processes listening on a TCP port; empty when lsof is unavailable."""
    try:
        pids = subprocess.check_output(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], stderr=subprocess.DEVNULL).decode().split()
    except (OSError, subprocess.CalledProcessError):
        return []
    found = []
    for pid in pids:
        command = subprocess.run(["ps", "-p", pid, "-o", "command="], capture_output=True, text=True).stdout.strip()
        found.append((int(pid), command))
    return found


def is_project_process(command: str) -> bool:
    """True for our own uvicorn/vite processes (their command lines carry the project path or module)."""
    return str(PROJECT_DIR) in command or "src.api.server" in command


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def free_port(port: int, force: bool = False, *, find=listeners, kill=os.kill, alive=process_alive,
              grace_seconds: float = 3.0) -> None:
    """Stop this project's process on ``port`` (SIGTERM, then SIGKILL); refuse to touch anyone else's."""
    for pid, command in find(port):
        if not (force or is_project_process(command)):
            sys.exit(f"[HATA] Port {port} başka bir uygulama tarafından kullanılıyor (pid {pid}): {command}\n"
                     f"       Durdurup yeniden deneyin ya da yine de kapatmak için: python3 start.py --force")
        print(f"[BİLGİ] Port {port} için eski süreç durduruluyor (pid {pid}).")
        kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + grace_seconds
        while alive(pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        if alive(pid):
            kill(pid, signal.SIGKILL)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="kill whatever listens on ports 8000 and 5173")
    args = parser.parse_args()

    print("=" * 55)
    print("   ⚽ PREMIER LEAGUE MODEL & DASHBOARD LAUNCHER")
    print("=" * 55)

    if not shutil.which("npm"):
        sys.exit("[HATA] npm bulunamadı. Lütfen Node.js kurulu olduğundan emin olun.")

    free_port(8000, args.force)
    free_port(5173, args.force)

    # Check frontend node_modules
    if not (FRONTEND_DIR / "node_modules").exists():
        print("[BİLGİ] frontend/node_modules eksik, yükleniyor...")
        subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True)

    # 1. Start backend server
    print("[1/2] Model Backend API başlatılıyor (FastAPI / Port: 8000)...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.server:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=str(PROJECT_DIR),
    )

    time.sleep(1.5)

    # 2. Start frontend dev server
    print("[2/2] Web Arayüzü başlatılıyor (Vite / Port: 5173)...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(FRONTEND_DIR),
    )

    print("\n✔ SİSTEM HAZIR VE AKTİF!")
    print("-" * 55)
    print(" 🌐 Web Dashboard:            http://localhost:5173")
    print(" ⚙️  Model API:                http://127.0.0.1:8000")
    print(" 📖 Swagger Dokümantasyonu:    http://127.0.0.1:8000/docs")
    print("-" * 55)
    print("Durdurmak için [CTRL + C] tuşlarına basın.\n")

    def handle_signal(sig, frame):
        print("\n[KAPANIŞ] Servisler kapatılıyor...")
        try:
            backend_proc.terminate()
        except OSError:
            pass
        try:
            frontend_proc.terminate()
        except OSError:
            pass
        backend_proc.wait()
        frontend_proc.wait()
        print("[OK] Tüm servisler kapatıldı.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        handle_signal(None, None)


if __name__ == "__main__":
    main()
