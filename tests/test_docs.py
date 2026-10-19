import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "scripts_reference.md").read_text(encoding="utf-8")
MENTIONED = set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:py|sh))`", DOC))
EXISTING = {p.name for p in ROOT.rglob("*") if p.suffix in {".py", ".sh"} and "node_modules" not in p.parts and ".git" not in p.parts}


def test_every_source_and_test_file_is_described_in_the_script_reference():
    files = [p for folder in ("src", "tests") for p in (ROOT / folder).rglob("*.py") if p.name != "__init__.py"]
    undocumented = sorted(str(p.relative_to(ROOT)) for p in files if p.name not in {m.split("/")[-1] for m in MENTIONED})
    assert not undocumented, f"add these to docs/scripts_reference.md: {undocumented}"


def test_the_script_reference_names_no_file_that_does_not_exist():
    missing = sorted(m for m in MENTIONED if m.split("/")[-1] not in EXISTING)
    assert not missing, f"docs/scripts_reference.md mentions files that no longer exist: {missing}"
