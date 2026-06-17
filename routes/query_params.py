"""
Parse optional query-string parameters for GET routes.

Flask exposes the query string (the part after "?" in the URL) as
``request.args``. Values are always strings until you convert them.

Example URL:
    /api/dashboard?simulations=5000&seed=42

This module is imported by route modules. It must only run *inside* a
request (when a view function calls these helpers), never at import time.
"""

from __future__ import annotations
from typing import Any
from flask import abort, request

def _override_fixtures_from_request(default: list[dict[str, Any] | None]):

    if "overrides" not in request.args:
        return default

    raw = request.args.get("overrides", type= list[dict[str, Any]])

    if raw is None or raw.strip() == "":
        abort(400, description="Query parameter 'overrides' must be a list of fixtures if provided.")

    try:
        return raw
    except ValueError:
        abort(400, description=f"Query parameter 'overrides' must be an list, got {raw!r}.")

def _accuracy_gameweek_from_request(default: int):
    '''
    Read optional ``?gameweek=`` from the query string, or use *default*.
    Args:
        default: set in the config module, will be midway through season (gameweek = 17)

    Returns: parsed integer for gameweek from query
    '''

    if "gameweek" not in request.args:
        return default

    raw = request.args.get("gameweek", type=str)
    if raw is None or raw.strip() == "":
        abort(400, description="Query parameter 'gameweek' must be a non-empty string if provided.")
    try:
        return str(raw)
    except ValueError:
        abort(400, description=f"Query parameter 'gameweek' must be an int, got {raw!r}.")


def _accuracy_season_from_request(default: str):
    """
    Read optional ``?season=`` from the query string, or use *default*.

    Args:
        default: default season string such as "2024"

    Returns:
        Validated season string.
    """

    if "season" not in request.args:
        return default

    raw = request.args.get("season")

    if raw is None or raw.strip() == "":
        abort(
            400,
            description="Query parameter 'season' must be a non-empty string if provided."
        )

    raw = raw.strip()

    try:
        if int(raw) >= 2025:
            abort(
                400,
                description="Query parameter 'season' must be prior to the 2025 season."
            )
    except ValueError:
        abort(
            400,
            description=f"Query parameter 'season' must be a string representing a year, got {raw!r}."
        )

    return raw
def _accuracy_checkpoints_from_request(default: list[int]) -> list[int]:
    '''
    Read optional ``?checkpoints=`` from the query string, or use *default*.
    Args: default checkpoints e.i [5, 10, 15, 20]

    Returns: validated checkpoints list
    '''

    checkpoints = request.args.get("checkpoints")
    # 1. Check if empty, could return defaults here if is empty
    if not checkpoints:
        abort(400, description="List of checkpoints should not be empty")

    # 2. Type validation (ensure they are integers)
    try:
        validate_checkpoints = [int(i) for i in checkpoints]
    except ValueError:
        abort(400, description="All checkpoints must be integers")

    checkpoints = [int(x) for x in checkpoints]
    return checkpoints