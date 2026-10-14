import pandas as pd

from src.features.draw_features import DRAW_PROPENSITY_FEATURES, DrawFeatureState, add_draw_features


def _matches():
    return pd.DataFrame([
        {"match_id": 1, "kickoff_millis": 1000, "home_id": 10, "away_id": 20,
         "home_score": 0, "away_score": 0, "gameweek": 1},
        {"match_id": 2, "kickoff_millis": 2000, "home_id": 20, "away_id": 30,
         "home_score": 2, "away_score": 1, "gameweek": 2},
        {"match_id": 3, "kickoff_millis": 2000, "home_id": 30, "away_id": 10,
         "home_score": 1, "away_score": 1, "gameweek": 2},
        {"match_id": 4, "kickoff_millis": 3000, "home_id": 10, "away_id": 30,
         "home_score": 0, "away_score": 2, "gameweek": 3},
    ]).set_index("match_id")


def test_a_match_result_does_not_change_its_own_features():
    matches = _matches()
    changed_result = matches.copy()
    changed_result.loc[3, ["home_score", "away_score"]] = [5, 0]

    original_features = add_draw_features(matches)
    changed_features = add_draw_features(changed_result)

    pd.testing.assert_series_equal(
        original_features.loc[3, DRAW_PROPENSITY_FEATURES],
        changed_features.loc[3, DRAW_PROPENSITY_FEATURES],
    )


def test_simultaneous_kickoff_results_do_not_leak_between_matches():
    matches = _matches()
    changed_peer = matches.copy()
    changed_peer.loc[2, ["home_score", "away_score"]] = [0, 0]

    original_features = add_draw_features(matches)
    changed_features = add_draw_features(changed_peer)

    pd.testing.assert_series_equal(
        original_features.loc[3, DRAW_PROPENSITY_FEATURES],
        changed_features.loc[3, DRAW_PROPENSITY_FEATURES],
    )


def test_live_state_matches_offline_features_after_same_history():
    matches = _matches()
    history = matches.loc[[1, 2, 3]]
    upcoming = matches.loc[[4]]

    offline = add_draw_features(matches).loc[4, DRAW_PROPENSITY_FEATURES]
    state = DrawFeatureState()
    for row in history.sort_values(["kickoff_millis"]).itertuples():
        state.update(row.home_id, row.away_id, row.home_score, row.away_score)
    live = pd.Series(state.features(10, 30, gameweek=3))

    pd.testing.assert_series_equal(offline, live[offline.index], check_names=False)
