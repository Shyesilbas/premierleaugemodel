"""Every data tool explains itself: --help works without side effects and says what it reads, writes and needs."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INGEST_TOOLS = (
    "sync_competition", "sync_competition_data", "sync_thestatsapi_competition", "fetch_thestatsapi_league",
    "load_thestatsapi_league", "fetch_openfootball_schedule", "fetch_team_badges", "export_competition_raw",
)


def run(*args):
    return subprocess.run([sys.executable, *args, "--help"], cwd=ROOT, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("tool", INGEST_TOOLS)
def test_ingest_tool_help_describes_usage_inputs_and_outputs(tool):
    result = run("-m", f"src.ingest.{tool}")
    assert result.returncode == 0, result.stderr
    text = result.stdout
    assert "Usage:" in text and "python3 -m src.ingest." in text
    assert any(word in text for word in ("Writes", "Reads", "writes", "Writes:"))
    assert any(word in text.lower() for word in ("key", "needs"))


def test_ingest_index_lists_every_tool_and_the_source_map():
    text = run("-m", "src.ingest").stdout
    for tool in INGEST_TOOLS:
        assert tool in text
    assert "docs/data_sources.md" in text


def test_research_ablation_help_does_not_run_the_experiment():
    result = run("research/box_features_ablation.py")
    assert result.returncode == 0 and "--output" in result.stdout and "Writes:" in result.stdout


def test_pipeline_help_points_to_the_other_tools():
    assert "src.ingest --help" in run("run_full_pipeline.py").stdout


def test_data_sources_page_mentions_every_new_tool():
    page = (ROOT / "docs" / "data_sources.md").read_text(encoding="utf-8")
    for tool in INGEST_TOOLS:
        assert f"src.ingest.{tool}" in page, tool
    assert "research/box_features_ablation.py" in page


def test_league_trainer_help_describes_protocol_and_outputs():
    result = run("-m", "src.models.train_league_model")
    assert result.returncode == 0 and "walk-forward" in result.stdout and "Writes" in result.stdout and "Needs" in result.stdout
