"""File helpers shared by the ingest scripts."""

import json
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, payload: Any) -> None:
    """Write JSON next to the target and rename it into place, so readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    temp_path.replace(path)
