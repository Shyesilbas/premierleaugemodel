#!/usr/bin/env bash
# Premier League Model Engine & Dashboard başlatıcı: asıl iş start.py içinde (tek kaynak).
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/start.py" "$@"
