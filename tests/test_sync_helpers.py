import json
import tempfile
from pathlib import Path

from src.ingest import sync_season_data as sync


def _fixture(status=None, scores=(None, None), outcome=None):
    teams = [{"team": {"name": "Brighton & Hove Albion"}, "score": scores[0]}, {"team": {"name": "Man City"}, "score": scores[1]}]
    return {"id": 5, "status": status, "outcome": outcome, "teams": teams}


def test_completed_follows_status_and_falls_back_to_scores():
    assert sync.fixture_is_completed(_fixture(status="C"))
    assert not sync.fixture_is_completed(_fixture(status="U", scores=(2, 1)))  # explicit status wins
    assert sync.fixture_is_completed(_fixture(scores=(2, 1)))
    assert not sync.fixture_is_completed(_fixture())
    assert not sync.fixture_is_completed(None)


def test_scores_and_team_names_survive_missing_data():
    assert sync.scores(_fixture(scores=(3, 0))) == (3, 0)
    assert sync.scores({"teams": []}) == (None, None)
    assert sync.fixture_pair(_fixture()) == ("brightonhovealbion", "manchestercity")
    assert sync.fixture_pair({"teams": []}) == ("", "")
    assert sync.match_label({"id": 9, "teams": []}) == "9"


def test_team_name_aliases_match_the_provider_spellings():
    assert sync.normalize_team_name("Nott'm Forest") == sync.normalize_team_name("Nottingham Forest") == "nottinghamforest"
    assert sync.normalize_team_name("Spurs") == "tottenhamhotspur"
    assert sync.normalize_team_name("Man Utd") != sync.normalize_team_name("Man City")


def test_main_referee_is_found_in_both_payload_shapes_and_ignored_when_absent():
    nested = [{"type": "Referee", "official": {"name": {"display": "Michael Oliver"}}}]
    flat = [{"role": "MAIN", "name": {"display": "Anthony Taylor"}}]
    assert sync.main_referee_name(nested) == "Michael Oliver"
    assert sync.main_referee_name(flat) == "Anthony Taylor"
    assert sync.main_referee_name([{"type": "Assistant", "official": {"name": {"display": "X"}}}]) is None
    assert sync.main_referee_name(None) is None


def test_details_have_main_referee_reads_the_cached_file():
    with tempfile.TemporaryDirectory() as tmp:
        good, bad, missing = Path(tmp) / "a.json", Path(tmp) / "b.json", Path(tmp) / "c.json"
        good.write_text(json.dumps({"matchOfficials": [{"role": "MAIN", "name": {"display": "Referee A"}}]}))
        bad.write_text("{not json")
        assert sync.details_have_main_referee(good)
        assert not sync.details_have_main_referee(bad)
        assert not sync.details_have_main_referee(missing)


def test_fixture_file_loader_accepts_both_layouts():
    with tempfile.TemporaryDirectory() as tmp:
        as_list, as_content = Path(tmp) / "a.json", Path(tmp) / "b.json"
        as_list.write_text(json.dumps([{"id": 1}]))
        as_content.write_text(json.dumps({"content": [{"id": 2}]}))
        assert sync.load_fixture_file(as_list) == [{"id": 1}]
        assert sync.load_fixture_file(as_content) == [{"id": 2}]
        assert sync.load_fixture_file(Path(tmp) / "missing.json") == []
