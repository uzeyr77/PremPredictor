"""
Service orchestration layer for Flask routes.

- Repository = data access
- `services.predictions` = engine math
- This module = JSON/template-facing orchestration
"""

from dataclasses import dataclass
from typing import Any
from datetime import datetime

from models.contracts import DashboardSummary, TeamProbabilityRow
from services.repository import PredictionRepository
from services.simulation_config import SimulationConfig, DEFAULT_SIMULATION_CONFIG
from services.validators import validate_fixture_override

from services.predictions import get_team_probabilities, league_table, backtest_model, get_accuracy_trend
from services.predictions import simulate_season
from services.predictions import get_project_final_points
from services import predictions as pred


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
        """
        now = datetime.now()
        sims = simulate_season(simulations, seed)
        projected = get_project_final_points()

        title_probabilities = sims["title_probabilities"]
        top_4_probs = sims["top_4_probabilities"]

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

    def get_detailed_predictions(
        self,
        simulations: int,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Build payload for /predictions page and API.
        """
        team_probabilities = get_team_probabilities(10_000)
        projected = get_project_final_points()
        all_points_distribution = simulate_season(10_000, seed)["points_distribution"]
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
            dist = pred.get_team_points_distribution(all_points_distribution[team])

            confidence_intervals.append({
                "team": team,
                "median": round(dist["median"]),
                "p5": round(dist["p5"]),
                "p95": round(dist["p95"])
            })

        return {
            "meta": {
                "simulation_count": simulations,
                "seed": seed
            },
            "projected_table": projected_table,
            "probabilities": probabilities,
            "confidence_intervals": confidence_intervals,
        }

    def get_upcoming_fixtures(self) -> list[dict[str, Any]]:
        """Build payload for upcoming fixture page."""
        fixture_df = pred.get_remaining_matches()
        payload = []

        for index, match in fixture_df.iterrows():
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

    def run_scenario(
        self,
        overrides: list[dict[str, str]],
        simulations: int,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Execute what-if scenario and return deltas against baseline."""
        for scenario in overrides:
            validate_fixture_override(scenario, set(league_table["team"]))

        team_probabilities = pred.get_team_probabilities(simulations)
        scenario_probabilities = pred.simulate_scenario(overrides, simulations, seed)

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

        scenario = {
            "title": {
                team: round(scenario_probabilities["title_probabilities"][team] * 100, 1)
                for team in league_table["team"]
            },
            "top2": {
                team: round(scenario_probabilities["top_2_probabilities"][team] * 100, 1)
                for team in league_table["team"]
            },
            "top4": {
                team: round(scenario_probabilities["top_4_probabilities"][team] * 100, 1)
                for team in league_table["team"]
            },
            "relegation": {
                team: round(scenario_probabilities["relegation_probabilities"][team] * 100, 1)
                for team in league_table["team"]
            }
        }

        def compare_metric(metric_key: str) -> list[dict[str, Any]]:
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

        comparison: dict[str, list[dict[str, Any]]] = {
            "title": compare_metric("title"),
            "top_4": compare_metric("top4"),
            "top_2": compare_metric("top2"),
            "relegation": compare_metric("relegation"),
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

    def get_accuracy_tracking(self, season: str, at_gameweek: int, checkpoints: list[int]) -> dict[str, Any]:
        """Build payload for /accuracy page."""
        freshness = pred.get_data_freshness_metadata()
        latest = backtest_model(season, at_gameweek)
        trend = pred.get_accuracy_trend(season, checkpoints)
        team_error_profile = pred.get_team_error_profile(season, at_gameweek)
        now = datetime.now()
        return {
            "meta": {
                "generated_at": now.isoformat(),
                "season": 2024,
                "at_gameweek": at_gameweek
            },
            "latest": latest,
            "trend": trend,
            "team_error_profile": team_error_profile,
            "freshness": freshness
        }
