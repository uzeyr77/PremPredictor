"""Detailed prediction routes."""

from flask import Blueprint, current_app, jsonify, render_template, request


# Blueprint object for all /predictions and /api/predictions endpoints.
predictions_bp = Blueprint("predictions", __name__)


def _build_detailed_predictions():
    """
    Shared payload builder for predictions page + predictions API.
    """
    cfg = current_app.config["APP_CONFIG"]
    service = current_app.config["PREDICTION_SERVICE"]
    return service.get_detailed_predictions(cfg.defualt_simulations, cfg.defualt_seed)


def _build_scenario_payload():
    """
    Validate and parse POST /api/scenario input, then call service.

    Request contract:
    {
      "overrides": [{"home": "...", "away": "...", "result": "home_win|draw|away_win"}],
      "simulations": 5000,   # optional
      "seed": 42             # optional
    }

    Behavior:
    - If simulations/seed are omitted from JSON body, fall back to query params.
    - If still omitted, query helpers fall back to AppConfig defaults.
    Edge Case:
    - if overrides list is missing just run baseline scenario (so it would be baseline vs baseline)

    - Simulations and Seed should be in json body as per the paylaod from prediction_service function, it is in the body of the dict
    with the key metadata which is why the body of the json is checked first
    """
    cfg = current_app.config["APP_CONFIG"]
    service = current_app.config["PREDICTION_SERVICE"]

    # Read JSON body; reject malformed or missing JSON early.
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400
    if not isinstance(body, dict):
        return jsonify({"error": "JSON body must be an object."}), 400

    # Validate overrides shape at route boundary before service logic.
    overrides = body.get("overrides")
    if overrides is None:
        # if overrides is present, then overrides is set to that user inputted value, otherwise it fallsback to []
        overrides = body.get("overrides", [])
        # return jsonify({"error": "Missing required key 'overrides'."}), 400
    if not isinstance(overrides, list):
        return jsonify({"error": "'overrides' must be a list."}), 400

    # simulations: prefer JSON body value; otherwise query helper/default.
    if "simulations" in body:
        raw_simulations = body["simulations"]
        if not isinstance(raw_simulations, int) or raw_simulations < 1:
            return jsonify({"error": "'simulations' must be an integer >= 1."}), 400
        simulations = raw_simulations
    else:
        simulations = _simulations_from_request(cdefault_simulations)

    # seed: prefer JSON body value; otherwise query helper/default.
    if "seed" in body:
        raw_seed = body["seed"]
        if raw_seed is not None and not isinstance(raw_seed, int):
            return jsonify({"error": "'seed' must be an integer or null."}), 400
        seed = raw_seed
    else:
        seed = _seed_from_request(cfg.default_seed)

    try:
        payload = service.run_scenario(overrides, simulations, seed)
    except ValueError as exc:
        # Service validators raise ValueError for unknown team / invalid result, etc.
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload), 200


@predictions_bp.get("/predictions")
def predictions_page():
    """
    Render detailed predictions page.
    """

    payload = _build_detailed_predictions()
    return render_template("predictions.html", **payload)


@predictions_bp.get("/api/predictions")
def predictions_api():
    """
    Return full prediction payload for frontend usage.
    """
    payload = _build_detailed_predictions()

    return jsonify(payload)


@predictions_bp.post("/api/scenario")
def scenario_api():
    """
    Apply scenario overrides and return probability deltas.
    """
    return _build_scenario_payload()
