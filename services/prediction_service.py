"""
Service orchestration layer for Flask routes.

- Repository = data access
- `services.predictions` = engine math
- This module = JSON/template-facing orchestration
"""
import json
from dataclasses import dataclass
from typing import Any
from datetime import datetime, timezone

from config import AppConfig
from models.contracts import (
    DashboardMeta,
    DashboardSummary,
    FeaturedMatchCard,
    FeaturedMatches,
    HeroMatchCard,
    TeamProbabilityRow,
)

from services.validators import validate_fixture_override

from services.predictions import *
from services.repository import PredictionRepository


def _fixture_pair(fixture: dict | None) -> tuple[str, str] | None:
    if not fixture:
        return None
    return fixture["home_team"], fixture["away_team"]


def build_featured_spotlights(
    featured_matches: FeaturedMatches,
    hero_match: HeroMatchCard | None,
) -> list[FeaturedMatchCard]:
    """Big-match and derby cards that are not already the hero fixture."""
    hero_pair = _fixture_pair(hero_match)
    spotlights: list[FeaturedMatchCard] = []
    for key in ("big_match", "derby"):
        match = featured_matches.get(key)
        if match and _fixture_pair(match) != hero_pair:
            spotlights.append(match)
    return spotlights


@dataclass
class PredictionService:
    repository: PredictionRepository
    config: AppConfig

    def get_dashboard_summary(
        self,
    ) -> DashboardSummary:
        """Build the full dashboard payload for `/` and `/api/dashboard`."""
        fp = self.repository.db_fingerprint()
        cache = self.repository.get_cached_payload('dashboard')
        sims = self.config.default_simulations
        seed = self.config.default_seed
        # if the cache is found in the table, and it matches the current fingerprint, and it is not expired
        # then it is a cache hit and there is no compute required

        if cache and fp == cache['fingerprint'] and not self._expired(cache['computed_at']):
            return json.loads(cache['payload'])
        else:
            payload = self.compute_dashboard_summary(sims, seed)
            self.repository.upsert_cache('dashboard', fp, payload)
            return payload

    def _expired(self, time_stored: str) -> bool:

        curr_time = datetime.now(timezone.utc)
        elapsed_time = (curr_time - datetime.fromisoformat(time_stored)).total_seconds()

        return elapsed_time > 1800



    def get_detailed_predictions(
        self,
        simulations: int,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """
        Build payload for /predictions page and API.
        """
        league_table = self.repository.get_current_table()
        simulation_results = simulate_season(self.repository, simulations, seed)

        team_probabilities = get_team_probabilities(self.repository, simulations, simulation_results)
        projected = get_project_final_points(self.repository)
        all_points_distribution = simulation_results["points_distribution"]
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
            dist = get_team_points_distribution(all_points_distribution[team])
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
        """Build payload for upcoming fixture page (with predictions)."""
        upcoming_fixture_df = predict_all_remaining_matches(self.repository)
        payload = []

        for index, match in upcoming_fixture_df.iterrows():
            entry = {
                'date': match['date'],
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'home_win_prob': match['home_win_prob'],
                'draw_prob': match['draw_prob'],
                'away_win_prob': match['away_win_prob'],
                'expected_home_goals': match['expected_home_goals'],
                'expected_away_goals': match['expected_away_goals']
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
        league_table = self.repository.get_current_table()
        for scenario in overrides:
            validate_fixture_override(scenario, set(league_table["team"]))

        team_probabilities = get_team_probabilities(self.repository, simulations)
        scenario_probabilities = simulate_scenario(self.repository, overrides, simulations, seed)

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

    def get_accuracy_tracking(self, season: int, at_gameweek: int, checkpoints: list[int]) -> dict[str, Any]:
        """Build payload for /accuracy page."""
        freshness = get_data_freshness_metadata()
        latest = backtest_model(self.repository, season, at_gameweek)
        trend = get_accuracy_trend(self.repository, season, checkpoints)
        team_error_profile = get_team_error_profile(self.repository, season, at_gameweek)
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
    
    def compute_dashboard_summary(
        self,
        simulations: int,
        seed: int | None = None,
    ) -> DashboardSummary:
        """Build the full dashboard payload for `/` and `/api/dashboard`."""
        now = datetime.now()
        sims = simulate_season(self.repository, simulations, seed)
        projected = get_project_final_points(self.repository)

        pool = get_featured_fixture_pool(self.repository)
        league_table = self.repository.get_current_table()

        critical_match, critical_games = analyze_pool_swings(
            self.repository,
            pool,
            sims,
            simulations,
            seed,
        )
        featured_matches: FeaturedMatches = {
            "big_match": pick_big_match(pool, league_table),
            "derby": pick_derby_from_pool(pool),
            "critical_match": critical_match,
        }

        title_probabilities = sims["title_probabilities"]
        top_4_probs = sims["top_4_probabilities"]
        releg_probs = sims["relegation_probabilities"]
        top3_teams = sorted(title_probabilities, key=title_probabilities.get, reverse=True)[:3]
        top4_teams = sorted(top_4_probs, key=top_4_probs.get, reverse=True)[:4]
        releg_teams = sorted(releg_probs, key=releg_probs.get, reverse=True)[:3]

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
        relegation_race: list[TeamProbabilityRow] = [
            {
                "team": team,
                "title_probability": title_probabilities[team],
                "top_4_probability": top_4_probs[team],
                "relegation_probability": releg_probs[team],
            }
            for team in releg_teams
        ]

        meta: DashboardMeta = {
            "matchweek": self.repository.get_matchweek(),
            "season": 2025,
            "season_label": "2025/26",
        }

        hero_match = build_hero_match(
            self.repository,
            featured_matches,
            sims,
            simulations,
            seed,
        )

        payload: DashboardSummary = {
            "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
            "simulation_count": simulations,
            "meta": meta,
            "title_favorites": title_favs,
            "top_4_race": top_4_race,
            "relegation_race": relegation_race,
            "projected_table": build_rich_projected_table(
                self.repository,
                sims,
                projected,
                top_n=20,
                bottom_n=0,
            ),
            "upcoming_fixtures": annotate_upcoming_fixtures(pool, limit=6),
            "featured_matches": featured_matches,
            "featured_spotlights": build_featured_spotlights(featured_matches, hero_match),
            "critical_games": critical_games,
            "hero_match": hero_match,
            "form_pulse": get_form_pulse(self.repository),
        }
        return payload

