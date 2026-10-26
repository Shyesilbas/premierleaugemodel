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


def test_every_competition_in_the_config_is_described_in_the_data_source_map():
    import yaml

    config = yaml.safe_load((ROOT / "config" / "competitions.yaml").read_text(encoding="utf-8"))
    page = (ROOT / "docs" / "data_sources.md").read_text(encoding="utf-8")
    missing = [f"{key} ({info['id']})" for key, info in config["competitions"].items() if f"`competition_id` {info['id']}" not in page and f"({info['id']})" not in page]
    assert not missing, f"add these competitions to docs/data_sources.md: {missing}"


def test_every_ingest_command_is_in_the_index_and_the_index_names_only_real_tools():
    import ast

    from src.ingest.__main__ import TOOLS

    listed = {name for _, tools in TOOLS for name, _ in tools}
    commands = set()
    for path in (ROOT / "src" / "ingest").glob("*.py"):
        if path.name == "__main__.py":
            continue
        if '__name__ == "__main__"' in path.read_text(encoding="utf-8"):
            ast.parse(path.read_text(encoding="utf-8"))
            commands.add(path.stem)
    assert commands <= listed, f"add to the TOOLS index in src/ingest/__main__.py: {sorted(commands - listed)}"
    assert listed <= commands, f"the index names tools that are not commands: {sorted(listed - commands)}"


def test_agents_file_keeps_the_documentation_sync_rule():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Doküman ve Rapor Senkronu" in agents and "docs/data_sources.md" in agents
    for skill in (ROOT / ".agents" / "skills").glob("*/SKILL.md"):
        assert "Doküman ve Rapor Senkronu" in skill.read_text(encoding="utf-8") or "Documentation & Registry Synchronization" in skill.read_text(encoding="utf-8"), skill.name


def test_project_status_states_the_real_number_of_tests():
    import subprocess
    import sys

    status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    claimed = re.search(r"\*\*Testler:\*\* (\d+)/(\d+) geçiyor", status)
    assert claimed, "PROJECT_STATUS.md must state the number of passing tests as '**Testler:** N/N geçiyor.'"
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True, timeout=300).stdout
    collected = int(re.search(r"(\d+) tests? collected", out).group(1))
    assert int(claimed.group(2)) == collected, f"PROJECT_STATUS.md says {claimed.group(2)} tests, pytest collects {collected}; update the number"
