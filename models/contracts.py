"""
Typed contracts for route/service responses.

Why this matters:
- Routes and templates can rely on stable keys.
- Future refactors become safer and easier to test.
"""

from typing import TypedDict, NotRequired, Any


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


class FeaturedMatchCard(TypedDict):
    home_team: str
    away_team: str
    date: str
    matchweek: int
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    badge: str
    expected_home_goals: NotRequired[float]
    expected_away_goals: NotRequired[float]
    expected_swing: NotRequired[float]


class FeaturedMatches(TypedDict):
    big_match: FeaturedMatchCard | None
    derby: FeaturedMatchCard | None
    critical_match: FeaturedMatchCard | None


class DashboardMeta(TypedDict):
    matchweek: int
    season: int
    season_label: str


class FormPulseTeam(TypedDict):
    team: str
    form: list[str]
    ppg: float


class FormPulse(TypedDict):
    in_form: list[FormPulseTeam]
    cold: list[FormPulseTeam]


class ProjectedTableRow(TypedDict):
    position: NotRequired[int]
    team: NotRequired[str]
    current_points: NotRequired[int]
    projected_points: NotRequired[int]
    title_probability: NotRequired[float]
    top_4_probability: NotRequired[float]
    relegation_probability: NotRequired[float]
    is_separator: NotRequired[bool]
    label: NotRequired[str]


class CriticalGameCard(FeaturedMatchCard):
    race: str
    metric: str
    swing: float


class StakeRow(TypedDict):
    race: str
    description: str
    team: str
    delta: float


class HeroMatchCard(FeaturedMatchCard):
    head_to_head: list[str]
    home_form: FormPulseTeam
    away_form: FormPulseTeam
    stakes: list[StakeRow]


class UpcomingFixtureCard(TypedDict):
    date: str
    home_team: str
    away_team: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    expected_home_goals: NotRequired[float]
    expected_away_goals: NotRequired[float]
    pick: str


class DashboardSummary(TypedDict):
    last_updated: str
    simulation_count: int
    meta: DashboardMeta
    title_favorites: list[TeamProbabilityRow]
    top_4_race: list[TeamProbabilityRow]
    relegation_race: list[TeamProbabilityRow]
    projected_table: list[ProjectedTableRow]
    upcoming_fixtures: list[UpcomingFixtureCard]
    featured_matches: FeaturedMatches
    featured_spotlights: list[FeaturedMatchCard]
    critical_games: list[CriticalGameCard]
    hero_match: HeroMatchCard | None
    form_pulse: FormPulse


class ApiError(TypedDict):
    error: str
    detail: str
