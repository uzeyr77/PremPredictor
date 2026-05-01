"""
Typed contracts for route/service responses.

Why this matters:
- Routes and templates can rely on stable keys.
- Future refactors become safer and easier to test.
"""

from typing import TypedDict, NotRequired


class MatchPrediction(TypedDict):
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: float
    expected_away_goals: float


class TeamProbabilityRow(TypedDict):
    team: str
    title_probability: float
    top_4_probability: float
    top_2_probability: NotRequired[float]
    relegation_probability: NotRequired[float]


class DashboardSummary(TypedDict):
    last_updated: str
    simulation_count: int
    title_favorites: list[TeamProbabilityRow]
    top_4_race: list[TeamProbabilityRow]
    projected_table: list[dict]


class ApiError(TypedDict):
    error: str
    detail: str

