"""
Dashboard routes.

This blueprint handles:
- HTML page route for dashboard
- JSON API endpoint for dashboard payload
"""

from flask import Blueprint, current_app, jsonify, render_template


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def dashboard_page():
    """
    Server-rendered dashboard page.

    TODO:
    - Fetch PredictionService from app context.
    - Call get_dashboard_summary().
    - Pass payload into template.
    """
    return render_template("index.html")


@dashboard_bp.get("/api/dashboard")
def dashboard_api():
    """
    JSON dashboard endpoint.
    """
    return jsonify(
        {
            "status": "stub",
            "message": "TODO: implement /api/dashboard using PredictionService.",
            "app_name": current_app.name,
        }
    )

