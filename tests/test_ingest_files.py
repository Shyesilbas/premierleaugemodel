import json
import tempfile
from pathlib import Path

from src.ingest.files import atomic_write_json


def test_atomic_write_creates_parents_keeps_unicode_and_leaves_no_temp_file():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "a" / "b" / "details.json"
        atomic_write_json(target, {"name": "Gündoğan", "n": 1})
        assert json.loads(target.read_text(encoding="utf-8")) == {"name": "Gündoğan", "n": 1}
        assert "Gündoğan" in target.read_text(encoding="utf-8")  # ensure_ascii=False
        assert [p.name for p in target.parent.iterdir()] == ["details.json"]


def test_atomic_write_replaces_an_existing_file_in_one_step():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "x.json"
        atomic_write_json(target, {"v": 1})
        atomic_write_json(target, {"v": 2})
        assert json.loads(target.read_text()) == {"v": 2}
