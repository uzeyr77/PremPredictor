"""
Contract tests for `PredictionService`.

Organization:
- Tests are grouped into **classes** only for readability (pytest discovers methods
  named `test_*` inside classes the same way as module-level functions).
- **Mocked** tests patch heavy engine calls (`simulate_season`, etc.) so they run
  fast and do not require `prem_data.db`.
- **Integration** tests hit real imports / DB and are marked `@pytest.mark.integration`.

Patching rule of thumb:
  Patch where the name is **used**, i.e. ``services.prediction_service.simulate_season``,
  not `services.predictions.simulate_season`, because the service module binds the
  reference at import time.

References:
  https://docs.pytest.org/en/stable/how-to/monkeypatch.html
  https://docs.python.org/3/library/unittest.mock.html#unittest.mock.patch
"""

from __future__ import annotations

import json
import math
from unittest.mock import patch

import pandas as pd
import pytest

from services.prediction_service import PredictionService
from services.repository import PredictionRepository


# ---------------------------------------------------------------------------
# Helpers (not tests — pytest ignores functions that do not start with `test_`)
# ---------------------------------------------------------------------------


def _make_projected_points_df() -> pd.DataFrame:
    """
    Minimal DataFrame matching what `get_project_final_points()` returns:
    columns `team`, `projected_final_points`, `position`.

    `PredictionService.get_dashboard_summary` indexes by integer position:
    iat[i, 0] team, iat[i, 1] points, iat[i, 2] position.
    """
    return pd.DataFrame(
        {
            "team": ["Alpha FC", "Beta United", "Gamma City"],
            "projected_final_points": [88, 82, 76],
            "position": [1, 2, 3],
        }
    )


def _make_simulate_season_return() -> dict:
    """
    Dict shaped like `simulate_season()` / `simulate_scenario()` top-level return.

    Must include every team key used by `league_table` in integration tests;
    for mocked dashboard tests we only need enough teams for top-3 / top-4 slices.
    """
    teams = ["Alpha FC", "Beta United", "Gamma City"]
    title = {"Alpha FC": 0.50, "Beta United": 0.35, "Gamma City": 0.15}
    top4 = {"Alpha FC": 0.92, "Beta United": 0.88, "Gamma City": 0.40}
    points_dist = {t: [70 + i for i in range(20)] for t in teams}
    return {
        "title_probabilities": title,
        "top_4_probabilities": top4,
        "top_2_probabilities": {t: 0.5 for t in teams},
        "relegation_probabilities": {t: 0.05 for t in teams},
        "all_simulations": [],
        "points_distribution": points_dist,
    }


# ---------------------------------------------------------------------------
# Class 1 — Service can be constructed (sanity / constructor contract)
# ---------------------------------------------------------------------------


class TestPredictionServiceConstruction:
    """Verify the dataclass wiring expected by Flask `create_app` patterns."""

    def test_service_accepts_prediction_repository(self) -> None:
        """`PredictionService` requires a `PredictionRepository` instance."""
        repo = PredictionRepository(":memory:")
        svc = PredictionService(repository=repo)
        assert svc.repository is repo
        assert svc.simulation_config is not None


# ---------------------------------------------------------------------------
# Class 2 — Dashboard summary (mocked engine = fast, deterministic)
# ---------------------------------------------------------------------------


class TestGetDashboardSummaryMocked:
    """
    `get_dashboard_summary` calls `simulate_season` and `get_project_final_points`.

    We patch both so this test never touches SQLite or Monte Carlo randomness.
    """

    @patch("services.prediction_service.get_project_final_points")
    @patch("services.prediction_service.simulate_season")
    def test_dashboard_payload_matches_dashboard_summary_contract(
        self,
        mock_simulate_season,
        mock_get_project_final_points,
        prediction_service: PredictionService,
    ) -> None:
        mock_simulate_season.return_value = _make_simulate_season_return()
        mock_get_project_final_points.return_value = _make_projected_points_df()

        payload = prediction_service.get_dashboard_summary(simulations=123)

        # --- TypedDict `DashboardSummary` keys (see models/contracts.py)
        assert set(payload.keys()) == {
            "last_updated",
            "simulation_count",
            "title_favorites",
            "top_4_race",
            "projected_table",
        }

        # Echo simulation count from the argument, not the mock return value.
        assert payload["simulation_count"] == 123

        # Timestamp format produced by `strftime` in the service.
        assert isinstance(payload["last_updated"], str)
        assert len(payload["last_updated"]) >= 10

        # --- title_favorites: list of TeamProbabilityRow (top 3 title contenders)
        assert isinstance(payload["title_favorites"], list)
        assert len(payload["title_favorites"]) <= 3
        for row in payload["title_favorites"]:
            assert set(row.keys()) == {"team", "title_probability", "top_4_probability"}
            assert isinstance(row["team"], str)
            assert isinstance(row["title_probability"], float)
            assert isinstance(row["top_4_probability"], float)

        # --- top_4_race: top 4 by top_4 probability in mock data
        assert isinstance(payload["top_4_race"], list)
        assert len(payload["top_4_race"]) <= 4

        # --- projected_table: list of dict rows
        assert isinstance(payload["projected_table"], list)
        assert len(payload["projected_table"]) == 3
        for row in payload["projected_table"]:
            assert set(row.keys()) == {"position", "team", "points"}
            assert isinstance(row["position"], int)
            assert isinstance(row["team"], str)
            assert isinstance(row["points"], int)

        mock_simulate_season.assert_called_once_with(123)
        mock_get_project_final_points.assert_called_once()


# ---------------------------------------------------------------------------
# Class 3 — Scenario runner (mocked engine)
# ---------------------------------------------------------------------------


class TestRunScenarioMocked:
    """
    `run_scenario` validates overrides, builds baseline vs scenario dicts, comparisons.

    Empty `overrides` avoids validation errors and keeps `simulate_scenario` logic
    exercised with minimal fixture setup when patched.
    """

    @patch("services.prediction_service.pred.simulate_scenario")
    @patch("services.prediction_service.pred.get_team_probabilities")
    def test_run_scenario_empty_overrides_payload_shape(
        self,
        mock_get_team_probabilities,
        mock_simulate_scenario,
        prediction_service: PredictionService,
    ) -> None:
        teams = ["Alpha FC", "Beta United", "Gamma City"]

        def _per_team_probs() -> dict:
            return {
                t: {
                    "title_probability": 0.1,
                    "top_2_probabilities": 0.2,
                    "top_4_probability": 0.5,
                    "relegation_probabilities": 0.05,
                }
                for t in teams
            }

        mock_get_team_probabilities.return_value = _per_team_probs()

        sim_ret = _make_simulate_season_return()
        mock_simulate_scenario.return_value = sim_ret

        with patch(
            "services.prediction_service.league_table",
            pd.DataFrame({"team": teams}),
        ):
            out = prediction_service.run_scenario(overrides=[], simulations=50, seed=1)

        assert set(out.keys()) == {"meta", "overrides", "baseline", "scenario", "comparison"}
        assert out["overrides"] == []
        assert out["meta"]["simulation_count"] == 50
        assert out["meta"]["seed"] == 1

        for bucket in ("title", "top2", "top4", "relegation"):
            assert bucket in out["baseline"]
            assert bucket in out["scenario"]
            assert isinstance(out["baseline"][bucket], dict)
            assert isinstance(out["scenario"][bucket], dict)
            assert set(out["baseline"][bucket].keys()) == set(teams)

        comp = out["comparison"]
        for key in ("title", "top_4", "top_2", "relegation"):
            assert key in comp
            assert isinstance(comp[key], list)
            if comp[key]:
                row0 = comp[key][0]
                assert set(row0.keys()) >= {
                    "team",
                    "baseline_prob",
                    "scenario_prob",
                    "change",
                    "change_pct",
                }


# ---------------------------------------------------------------------------
# Class 4 — Accuracy tracking JSON safety (mocked engine)
# ---------------------------------------------------------------------------


class TestGetAccuracyTrackingMocked:
    """Ensure the payload is JSON-serializable (Flask `jsonify` requirement)."""

    @patch("services.prediction_service.pred.get_team_error_profile")
    @patch("services.prediction_service.pred.get_accuracy_trend")
    @patch("services.prediction_service.backtest_model")
    @patch("services.prediction_service.pred.get_data_freshness_metadata")
    def test_accuracy_tracking_json_dumps_round_trip(
        self,
        mock_freshness,
        mock_backtest,
        mock_trend,
        mock_profile,
        prediction_service: PredictionService,
    ) -> None:
        mock_freshness.return_value = {"season": 2024}
        mock_backtest.return_value = {
            "season": "2024",
            "at_gameweek": 10,
            "metrics": {"mae_points": 5.0},
        }
        mock_trend.return_value = []
        mock_profile.return_value = []

        payload = prediction_service.get_accuracy_tracking(
            season="2024",
            at_gameweek=10,
            checkpoints=[5, 10],
        )

        # If this raises, the service layer still leaks non-JSON types (datetime, numpy, set, etc.).
        text = json.dumps(payload)
        assert isinstance(text, str)
        assert "latest" in payload


# ---------------------------------------------------------------------------
# Class 5 — Upcoming fixtures (mocked)
# ---------------------------------------------------------------------------


class TestGetUpcomingFixturesMocked:
    """`get_upcoming_fixtures` maps rows from `get_remaining_matches()` to dicts."""

    @patch("services.prediction_service.pred.get_remaining_matches")
    def test_fixture_list_entries_have_stable_keys(
        self,
        mock_get_remaining,
        prediction_service: PredictionService,
    ) -> None:
        mock_get_remaining.return_value = pd.DataFrame(
            [
                {
                    "date": "2026-01-01",
                    "home_team": "A",
                    "away_team": "B",
                    "home_win_prob": 0.5,
                    "away_win_prob": 0.2,
                    "expected_home_goals": 1.4,
                    "expected_away_goals": 1.2,
                }
            ]
        )

        rows = prediction_service.get_upcoming_fixtures()
        assert len(rows) == 1
        entry = rows[0]
        assert set(entry.keys()) == {
            "match_date",
            "home_team",
            "away_team",
            "home_win_prob",
            "away_win_prob",
            "expected_home_goals",
            "expected_away_goals",
        }


# ---------------------------------------------------------------------------
# Class 6 — Integration (optional): real DB + real engine
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPredictionServiceIntegration:
    """
    These tests import `services.predictions`, which opens SQLite using the path
    inside that module (currently hardcoded). They only run when `prem_data.db`
    exists at project root — see `conftest.prem_db_path`.

    Run manually:
      pytest tests/test_prediction_service.py -m integration -v
    """

    def test_backtest_model_metrics_ranges_via_service_accuracy(
        self,
        prem_db_path: str,
        prediction_service: PredictionService,
    ) -> None:
        """End-to-end: backtest numbers should be finite and within plausible ranges."""
        payload = prediction_service.get_accuracy_tracking(
            season="2024",
            at_gameweek=38,
            checkpoints=[38],
        )
        latest = payload["latest"]
        m = latest["metrics"]
        assert math.isfinite(m["mae_points"])
        assert m["mae_points"] >= 0.0
        # Adjust keys if you renamed metrics (e.g. position_accuracy_pm1).
        if "top4_hit_count" in m:
            assert 0 <= m["top4_hit_count"] <= 4
