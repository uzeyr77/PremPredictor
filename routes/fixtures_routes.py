"""
Upcoming fixture routes.
"""

from flask import Blueprint, jsonify, render_template, current_app

# init blueprint
fixtures_bp = Blueprint("fixtures", __name__)

def _build_fixtures():
    service = current_app.config["PREDICTION_SERVICE"]
    return service.get_upcoming_fixtures()


@fixtures_bp.get("/fixtures")
def fixtures_page():
    """
    Render upcoming fixtures page.
    """
    fixtures = _build_fixtures()
    return render_template("fixtures.html", fixtures = fixtures)


@fixtures_bp.get("/api/fixtures")
def fixtures_api():
    """
    Return upcoming fixtures with probabilities and expected goals.
    """
    return jsonify(_build_fixtures())
