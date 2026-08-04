from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

scenario_bp = Blueprint("scenario", __name__)


def _get_service():
    return current_app.config["PREDICTION_SERVICE"]


@scenario_bp.get("/scenario")
def scenario_page():
    service = _get_service()
    baseline = service.get_scenario_baseline()  # Uses cache
    upcoming = service.get_upcoming_fixtures_fast()  # Uses cache or fast pool

    return render_template(
        "scenario.html",
        upcoming_fixtures=upcoming,
        baseline=baseline,
        meta=baseline.get("meta", {}),
    )


@scenario_bp.post("/api/scenario")
def scenario_api():
    service = _get_service()

    data = request.get_json() or {}
    raw_overrides = data.get("overrides", [])

    if not raw_overrides:
        return jsonify({"error": "No overrides provided"}), 400

    # Transform frontend keys to validator-expected keys
    outcome_map = {"home": "home_win", "draw": "draw", "away": "away_win"}
    overrides = []
    for o in raw_overrides:
        overrides.append({
            "home": o.get("home_team"),
            "away": o.get("away_team"),
            "result": outcome_map.get(o.get("outcome"), o.get("outcome")),
        })

    cached_baseline = service.get_scenario_baseline()
    result = service.run_scenario_fast(overrides, cached_baseline)
    return jsonify(result)
