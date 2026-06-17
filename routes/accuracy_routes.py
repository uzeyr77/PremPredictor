"""
Accuracy tracking routes.
"""

from flask import Blueprint, current_app, jsonify, render_template
from routes.query_params import _accuracy_gameweek_from_request, _accuracy_season_from_request, _accuracy_checkpoints_from_request

accuracy_bp = Blueprint("accuracy", __name__)


def _build_accuracy():
    service = current_app.config["PREDICTION_SERVICE"]
    cfg = current_app.config["APP_CONFIG"] # configs to get defaults

    gameweek = _accuracy_gameweek_from_request(cfg.default_gameweek_backtest)
    season = _accuracy_season_from_request(cfg.default_season_backtest)
    checkpoints =_accuracy_checkpoints_from_request(cfg.default_checkpoints)

    return service.get_accuracy_tracking(season, gameweek, checkpoints)

@accuracy_bp.get("/accuracy")
def accuracy_page():
    """
    Render model accuracy page.
    """
    checkpoints = _build_accuracy()
    return render_template("accuracy.html", checkpoints = checkpoints)


@accuracy_bp.get("/api/accuracy")
def accuracy_api():
    """
    Return backtest and tracking metrics.
    """
    return jsonify(_build_accuracy())
