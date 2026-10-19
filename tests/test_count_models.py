import logging
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge

from src.models import count_model
from src.models.model_utils import make_regression_pipeline
from src.models.train_cards import CURATED_FEATURES as CARD_FEATURES, train_cards_model
from src.models.train_corners import CURATED_FEATURES as CORNER_FEATURES, train_corners_model
from src.models.train_offsides import CURATED_FEATURES as OFFSIDE_FEATURES, train_offsides_model
from src.models.train_saves import CURATED_FEATURES as SAVE_FEATURES, train_saves_model
from src.models.train_throws import CURATED_FEATURES as THROW_FEATURES, train_throws_model

LOGGER = logging.getLogger("test_count_models")


def _matches(n=240, features=("f1", "f2", "f3"), target="total_x", seed=0):
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(rng.normal(size=(n, len(features))), columns=list(features))
    frame["match_id"] = np.arange(n)
    frame["kickoff_millis"] = 1_600_000_000_000 + np.arange(n)[::-1] * 86_400_000  # stored out of order on purpose
    frame["season"] = np.repeat(["2021_22", "2022_23", "2023_24", "2024_25"], n // 4)
    frame["is_played"] = True
    frame[target] = rng.poisson(np.exp(1.5 + 0.2 * frame[features[0]])).astype(float)
    return frame


def _write(frame, tmp):
    path = Path(tmp) / "features.parquet"
    frame.to_parquet(path)
    return str(path)


def test_dataset_loader_keeps_played_rows_with_a_target_in_kickoff_order():
    frame = _matches()
    frame.loc[:9, "total_x"] = np.nan
    frame.loc[10:19, "is_played"] = False
    with tempfile.TemporaryDirectory() as tmp:
        df, X, y, partial = count_model.load_count_dataset(_write(frame, tmp), "total_x", ["f1", "f2"], "Test", LOGGER)
    assert len(df) == 220 and list(X.columns) == ["f1", "f2"] and len(X) == len(y) == 220
    assert df["kickoff_millis"].is_monotonic_increasing and isinstance(partial, set)


def test_dataset_loader_fails_clearly_on_missing_file_target_or_features():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write(_matches(), tmp)
        with pytest.raises(FileNotFoundError, match="Run the full pipeline"):
            count_model.load_count_dataset(str(Path(tmp) / "nope.parquet"), "total_x", ["f1"], "Test", LOGGER)
        with pytest.raises(ValueError, match="Target column 'total_y'"):
            count_model.load_count_dataset(path, "total_y", ["f1"], "Test", LOGGER)
        with pytest.raises(ValueError, match="Test model features missing.*'nope'"):
            count_model.load_count_dataset(path, "total_x", ["f1", "nope"], "Test", LOGGER)


def test_top_features_rank_by_absolute_coefficient_in_both_formats():
    X = pd.DataFrame({"a": [0.0, 1.0, 2.0, 3.0], "b": [1.0, 0.0, 1.0, 0.0], "c": [3.0, 1.0, 2.0, 0.0]})
    y = 5.0 * X["a"] - 0.5 * X["b"]
    model = make_regression_pipeline(Ridge(alpha=1e-6), scale=False).fit(X, y)
    as_dict = count_model.top_features_of(model, ["a", "b", "c"], limit=2)
    assert list(as_dict)[0] == "a" and len(as_dict) == 2  # the dominant coefficient comes first, limit applies
    records = count_model.top_features_of(model, ["a", "b", "c"], as_records=True, limit=2)
    assert records[0]["feature"] == "a" and set(records[0]) == {"feature", "importance"} and len(records) == 2


def test_top_features_are_empty_for_a_model_without_importances():
    class Plain:
        def predict(self, X):
            return np.zeros(len(X))
    assert count_model.top_features_of(Plain(), ["a"]) == {}
    assert count_model.top_features_of(Plain(), ["a"], as_records=True) == []


def test_saved_artifact_carries_the_keys_the_api_reads():
    y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    with tempfile.TemporaryDirectory() as tmp:
        artifact = count_model.save_count_artifact(tmp, "m.joblib", "MODEL", ["a", "b"], {"baseline_mean": 3.0}, y, {"a": 1.0}, target_col="t")
        loaded = joblib.load(Path(tmp) / "m.joblib")
    assert loaded.keys() == artifact.keys()
    assert loaded["feature_names"] == loaded["feature_cols"] == ["a", "b"] and loaded["target_col"] == "t"
    assert loaded["baseline_mean"] == 3.0 and loaded["count_dispersion_alpha"] >= 0


TRAINERS = [
    ("corners", train_corners_model, CORNER_FEATURES, "total_corners", "corner_model_v1.joblib"),
    ("throws", train_throws_model, THROW_FEATURES, "total_throws", "throws_model_v1.joblib"),
    ("saves", train_saves_model, SAVE_FEATURES, "total_saves", "saves_model_v1.joblib"),
    ("cards", train_cards_model, CARD_FEATURES, "total_cards", "cards_model_v1.joblib"),
    ("offsides", train_offsides_model, OFFSIDE_FEATURES, "total_offsides", "offside_model_v1.joblib"),
]


@pytest.mark.parametrize("name, train, features, target, filename", TRAINERS, ids=[t[0] for t in TRAINERS])
def test_every_trainer_runs_on_synthetic_data_and_writes_a_usable_artifact(name, train, features, target, filename):
    frame = _matches(n=480, features=features, target=target, seed=3)
    with tempfile.TemporaryDirectory() as tmp:
        returned = train(data_path=_write(frame, tmp), model_output_dir=tmp)
        artifact = joblib.load(Path(tmp) / filename)
    metrics = artifact["metrics"]
    assert artifact["feature_names"] == list(features) and artifact["baseline_mean"] > 0
    assert metrics["train_samples"] > 0 and metrics["test_samples"] > 0 and np.isfinite(metrics["train_rmse"])
    assert artifact["model"].predict(frame[list(features)].head(5)).shape == (5,)
    # cards returns the whole artifact, the others only the metrics (the pipeline report depends on it)
    assert (returned.keys() == artifact.keys()) if name == "cards" else (returned["train_samples"] == metrics["train_samples"])
