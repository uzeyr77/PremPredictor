"""
Service orchestration layer for Flask routes.

Analogy:
- Repository = warehouse
- Prediction math = factory machinery
- Service = operations manager deciding what to run and what to return
"""

from dataclasses import dataclass
from typing import Any, TypedDict
from datetime import datetime

from pandas.core.window.doc import template_see_also

from app import predictions
from boilerplate.models.contracts import DashboardSummary, TeamProbabilityRow
from boilerplate.services.repository import PredictionRepository
from boilerplate.services.simulation_config import SimulationConfig, DEFAULT_SIMULATION_CONFIG


from services.predictions import get_team_probabilities, league_table
from services.predictions import simulate_season
from services.predictions import get_project_final_points
from services import predictions as pred

from validators import validate_fixture_override

@dataclass
class PredictionService:
    repository: PredictionRepository
    simulation_config: SimulationConfig = DEFAULT_SIMULATION_CONFIG

    def get_dashboard_summary(
        self,
        simulations: int,
        seed: int | None = None,
    ) -> DashboardSummary:
        """
        Build payload for dashboard page.

        TODO:
        1) Load current table + team stats + fixtures
        2) Compute projection + race probabilities
        3) Return stable contract matching DashboardSummary
        """
        now = datetime.now()
        sims = simulate_season(simulations)
        projected = get_project_final_points()

        title_probabilities = sims["title_probabilities"]  # dict: team -> prob
        top_4_probs = sims["top_4_probabilities"]  # dict: team -> prob

        top3_teams = sorted(title_probabilities, key=title_probabilities.get, reverse=True)[:3]
        top4_teams = sorted(top_4_probs, key=top_4_probs.get, reverse=True)[:4]

        title_favs: list[TeamProbabilityRow] = [
            {
                "team": team,
                "title_probability": title_probabilities[team],
                "top_4_probability": top_4_probs[team],
            }
            for team in top3_teams
        ]

        top_4_race: list[TeamProbabilityRow] = [
            {
                "team": team,
                "title_probability": title_probabilities[team],
                "top_4_probability": top_4_probs[team],
            }
            for team in top4_teams
        ]

        # projected columns from your engine: team, projected_final_points, position
        projected_table = [
            {
                "position": int(projected.iat[i, 2]),
                "team": projected.iat[i, 0],
                "points": int(projected.iat[i, 1]),
            }
            for i in range(len(projected))
        ]

        last_updated = now.strftime("%Y-%m-%d %H:%M:%S")

        payload: DashboardSummary = {
            "last_updated": last_updated,
            "simulation_count": simulations,
            "title_favorites": title_favs,
            "top_4_race": top_4_race,
            "projected_table": projected_table,
        }

        return payload
        raise NotImplementedError("TODO: implement dashboard payload assembly.")

    def get_detailed_predictions(
        self,
        simulations: int,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Build payload for /predictions page and API.

        TODO:
        - Include full projected table
        - Include title/top4/top2/relegation probabilities
        - Include confidence interval blocks
        """
        team_probabilities = get_team_probabilities(10_000)
        projected = get_project_final_points()
        sims = simulate_season(10_000)
        projected_table = [
            {
                "position": int(projected.iat[i, 2]),
                "team": projected.iat[i, 0],
                "points": int(projected.iat[i, 1]),
            }
            for i in range(len(projected))
        ]
        probabilities = {
            "title": {
                team: round(data["title_probability"] * 100, 1)
                for team, data in team_probabilities.items()
            },
            "top2": {
                team: round(data["top_2_probabilities"] * 100, 1)
                for team, data in team_probabilities.items()
            },
            "top4": {
                team: round(data["top_4_probability"] * 100, 1)
                for team, data in team_probabilities.items()
            },
            "relegation": {
                team: round(data["relegation_probabilities"] * 100, 1)
                for team, data in team_probabilities.items()
            }
        }

        confidence_intervals = []
        for team in league_table["team"]:
            dist = pred.get_points_distribution(team, sims)

            confidence_intervals.append({
                "team": team,
                "median": round(dist["median"]),
                "p5": round(dist["p5"]),
                "p95": round(dist["p95"])
            })

        payload = {
            "meta": {
                "simulation_count": simulations,
                "seed": seed
            },
            "projected_table": projected_table,
            "probabilities": probabilities,
            "confidence_intervals": confidence_intervals,
        }


        return payload


        raise NotImplementedError("TODO: implement detailed prediction payload.")

    def get_upcoming_fixtures(self) -> list[dict[str, Any]]:
        """
        Build payload for upcoming fixture page.
        """
        fixture_df = pred.predict_all_remaining_matches()
        payload = []

        for index, match in fixture_df().iterrows():
            entry = {
                "match_date": match["date"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_win_prob": match["home_win_prob"],
                "away_win_prob": match["away_win_prob"],
                "expected_home_goals": match["expected_home_goals"],
                "expected_away_goals": match["expected_away_goals"]
            }
            payload.append(entry)

        return payload
        raise NotImplementedError("TODO: implement fixture prediction payload.")

    def run_scenario(
        self,
        overrides: list[dict[str, str]],
        simulations: int,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute what-if scenario and return deltas against baseline.
        """

        # validate that the scenario given
        for scenario in overrides:
           validate_fixture_override(scenario,league_table["teams"])

        # get actual team probability and team probability after certain scenarios
        team_probabilities = pred.get_team_probabilities(simulations)
        scenario_probabilities = pred.simulate_scenario(overrides, simulations)

        # baseline is without the scenario
        baseline = {
            "title": {
                team: round(data["title_probability"] * 100, 1)
                for team, data in team_probabilities.items()
            },
            "top2": {
                team: round(data["top_2_probabilities"] * 100, 1)
                for team, data in team_probabilities.items()
            },
            "top4": {
                team: round(data["top_4_probability"] * 100, 1)
                for team, data in team_probabilities.items()
            },
            "relegation": {
                team: round(data["relegation_probabilities"] * 100, 1)
                for team, data in team_probabilities.items()
            }
        }

        # probabilities with specific scenarios
        scenario = {
            "title": {
                team: round(data["title_probability"] * 100, 1)
                for team, data in scenario_probabilities.items()
            },
            "top2": {
                team: round(data["top_2_probabilities"] * 100, 1)
                for team, data in scenario_probabilities.items()
            },
            "top4": {
                team: round(data["top_4_probability"] * 100, 1)
                for team, data in scenario_probabilities.items()
            },
            "relegation": {
                team: round(data["relegation_probabilities"] * 100, 1)
                for team, data in scenario_probabilities.items()
            }
        }

        # helper function metric key = "title_probs", "top4_probs"
        def compare_metric(metric_key: str) -> list[dict[str, Any]]:

            # a dictionary with (team, metric_value) e.i metric_key = "title_prob"
            # baseline_probs = { {"arsenal": 0.23, "man city": 0.77},
            baseline_probs = baseline[metric_key]
            scenario_probs = scenario[metric_key]

            rows: list[dict[str, Any]] = []
            for team in baseline_probs:
                b = baseline_probs[team]
                s = scenario_probs[team]
                change = s - b
                rows.append(
                    {
                        "team": team,
                        "baseline_prob": b,
                        "scenario_prob": s,
                        "change": change,
                        "change_pct": change * 100,
                    }
                )
            rows.sort(key=lambda r: abs(r["change"]), reverse=True)
            return rows
            # 4) Build comparison buckets

        comparison: dict[str, list[dict[str, Any]]] = {
            "title": compare_metric("title_probabilities"),
            "top_4": compare_metric("top_4_probabilities"),
            "relegation": compare_metric("relegation_probabilities"),
        }

        return {
            "meta": {
                "simulation_count": simulations,
                "seed": seed
            },

            "overrides": overrides,
            "baseline": baseline,
            "scenario": scenario,
            "comparison": comparison,

        }
        raise NotImplementedError("TODO: implement scenario simulation and comparison.")

    def get_accuracy_tracking(self) -> dict[str, Any]:
        """
        Build payload for /accuracy page.

        TODO:
        - Add backtest summaries
        - Add trend metrics by gameweek
        - Add model version and data timestamp
        """
        raise NotImplementedError("TODO: implement accuracy payload.")

