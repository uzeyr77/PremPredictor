"""
Accuracy tracking routes.
"""

from flask import Blueprint, jsonify, render_template


accuracy_bp = Blueprint("accuracy", __name__)


@accuracy_bp.get("/accuracy")
def accuracy_page():
    """
    Render model accuracy page.
    """
    return render_template("accuracy.html")


@accuracy_bp.get("/api/accuracy")
def accuracy_api():
    """
    Return backtest and tracking metrics.
    """
    return jsonify({"status": "stub", "message": "TODO: implement /api/accuracy."})
