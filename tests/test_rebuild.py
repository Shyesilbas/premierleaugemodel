import subprocess
from unittest import mock

from src.config import ROOT
from src.pipeline import rebuild


def _modules(run: mock.MagicMock) -> list[str]:
    return [call.args[0][2] for call in run.call_args_list]


def test_rebuild_runs_every_step_in_order_from_the_repo_root():
    with mock.patch.object(rebuild.subprocess, "run") as run:
        rebuild.rebuild_derived_data()
    assert _modules(run) == [
        "src.processing.process_season_data", "src.processing.build_player_index",
        "src.features.build_features", "src.db.database",
    ]
    assert all(call.kwargs["cwd"] == ROOT and call.kwargs["check"] for call in run.call_args_list)


def test_a_failing_step_stops_the_chain_and_names_the_step():
    def fail_on_features(command, **_):
        if command[2] == "src.features.build_features":
            raise subprocess.CalledProcessError(3, command)

    with mock.patch.object(rebuild.subprocess, "run", side_effect=fail_on_features) as run:
        try:
            rebuild.rebuild_derived_data()
        except rebuild.RebuildError as exc:
            assert "features" in str(exc) and "3" in str(exc)
        else:
            raise AssertionError("expected RebuildError")
    assert "src.db.database" not in _modules(run)


def test_skip_leaves_a_step_out_and_rejects_unknown_names():
    with mock.patch.object(rebuild.subprocess, "run") as run:
        rebuild.rebuild_derived_data(skip=["database"])
    assert "src.db.database" not in _modules(run)
    try:
        rebuild.rebuild_derived_data(skip=["nope"])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_cron_sync_and_weekly_pipeline_share_one_rebuild_function():
    import run_full_pipeline
    from src.ingest import sync_season_data

    assert sync_season_data.rebuild_derived_data is rebuild.rebuild_derived_data
    assert run_full_pipeline.rebuild_derived_data is rebuild.rebuild_derived_data


def test_stage_selection():
    from run_full_pipeline import STAGES, select_stages

    assert select_stages() == list(STAGES)
    assert select_stages(only="goals") == ["goals"]
    assert select_stages(skip="rebuild, audits") == ["counts", "outcome", "goals"]
    assert select_stages(only="goals,rebuild") == ["rebuild", "goals"]  # always pipeline order
    try:
        select_stages(only="models")
    except ValueError as exc:
        assert "models" in str(exc)
    else:
        raise AssertionError("expected ValueError")
