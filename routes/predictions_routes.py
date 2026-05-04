"""
Detailed prediction routes.
"""

from flask import Blueprint, jsonify, render_template


predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.get("/predictions")
def predictions_page():
    """
    Render detailed predictions page.
    """
    return render_template("predictions.html")


@predictions_bp.get("/api/predictions")
def predictions_api():
    """
    Return full prediction payload for frontend usage.
    """
    return jsonify({"status": "stub", "message": "TODO: implement /api/predictions."})


@predictions_bp.post("/api/scenario")
def scenario_api():
    """
    Apply scenario overrides and return probability deltas.
    """
    return jsonify({"status": "stub", "message": "TODO: implement /api/scenario."})
