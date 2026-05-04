"""
Upcoming fixture routes.
"""

from flask import Blueprint, jsonify, render_template


fixtures_bp = Blueprint("fixtures", __name__)


@fixtures_bp.get("/fixtures")
def fixtures_page():
    """
    Render upcoming fixtures page.
    """
    return render_template("fixtures.html")


@fixtures_bp.get("/api/fixtures")
def fixtures_api():
    """
    Return upcoming fixtures with probabilities and expected goals.
    """
    return jsonify({"status": "stub", "message": "TODO: implement /api/fixtures."})
