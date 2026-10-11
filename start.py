#!/usr/bin/env python3
"""
Premier League Model Engine & Dashboard Launcher
Starts FastAPI backend server and Vite frontend concurrently.
Gracefully shuts down both processes on Ctrl+C.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_DIR / "frontend"


def free_port(port: int):
    """Terminates processes listening on the given port to avoid address-in-use errors."""
    try:
        output = subprocess.check_output(["lsof", "-ti", f":{port}"], stderr=subprocess.DEVNULL)
        pids = [p.strip() for p in output.decode().split() if p.strip()]
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except OSError:
                pass
        if pids:
            time.sleep(0.5)
    except Exception:
        pass


def main():
    print("=" * 55)
    print("   ⚽ PREMIER LEAGUE MODEL & DASHBOARD LAUNCHER")
    print("=" * 55)

    # Free active ports if any
    free_port(8000)
    free_port(5173)

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
