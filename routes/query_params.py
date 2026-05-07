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


def _simulations_from_request(default: int) -> int:
    """
    Read ``?simulations=`` from the query string, or use *default*.

    Rules:
    - If the client omits ``simulations``, return *default* (from AppConfig).
    - If the client sends ``simulations`` but it is not a valid integer,
      respond with HTTP 400 (bad request).

    Why 400? The client sent malformed input; that is their mistake, not a
    server bug (500).
    """
    # ``in request.args`` is True only when the key appears in the query string.
    # That distinguishes "missing" from "present but wrong" when we need to.
    if "simulations" not in request.args:
        return default

    # Raw value is still a string, e.g. "5000" or "not_a_number".
    raw = request.args.get("simulations", type=str)
    if raw is None or raw.strip() == "":
        abort(400, description="Query parameter 'simulations' must be a non-empty integer.")

    try:
        value = int(raw)
    except ValueError:
        abort(400, description=f"Query parameter 'simulations' must be an integer, got {raw!r}.")

    if value < 1:
        abort(400, description="Query parameter 'simulations' must be at least 1.")

    return value


def _seed_from_request(default: int | None) -> int | None:
    """
    Read optional ``?seed=`` from the query string, or use *default*.

    *default* is often ``None`` (no fixed seed — Monte Carlo varies run to run).
    If the client sends ``seed``, it must be a valid integer.
    """
    if "seed" not in request.args:
        return default

    raw = request.args.get("seed", type=str)
    if raw is None or raw.strip() == "":
        abort(400, description="Query parameter 'seed' must be a non-empty integer if provided.")

    try:
        return int(raw)
    except ValueError:
        abort(400, description=f"Query parameter 'seed' must be an integer, got {raw!r}.")

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