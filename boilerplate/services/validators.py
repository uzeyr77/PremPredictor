"""
Validation helpers for route payloads and simulation inputs.

Why:
- Catch bad input at the boundary.
- Keep service logic focused on modeling, not error formatting.
"""


def validate_team_name(team: str, valid_teams: set[str]) -> None:
    """
    Validate that a team exists in your canonical team set.
    """

    if team not in valid_teams:
        raise ValueError(f"Unknown team: {team}")


def validate_probability_triplet(home_win: float, draw: float, away_win: float) -> None:
    """
    Basic probability integrity check.
    """
    total = home_win + draw + away_win
    if abs(total - 1.0) > 0.05:
        raise ValueError(f"Invalid probability sum: {total:.4f}")


def validate_fixture_override(override: dict, valid_teams: set[str]) -> None:
    """
    Expected override shape:
    {
      'home': 'Arsenal',
      'away': 'Liverpool',
      'result': 'home_win' | 'draw' | 'away_win'
    }
    """

    required = {"home", "away", "result"}
    if not required.issubset(set(override.keys())):
        raise ValueError("Override missing required keys: home, away, result")

    validate_team_name(override["home"], valid_teams)
    validate_team_name(override["away"], valid_teams)

    if override["result"] not in {"home_win", "draw", "away_win"}:
        raise ValueError("Override result must be home_win, draw, or away_win")

