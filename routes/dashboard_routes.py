from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template

dashboard_bp = Blueprint("dashboard", __name__)


def _build_dashboard_summary():
    service = current_app.config["PREDICTION_SERVICE"]
    return service.get_dashboard_summary()


@dashboard_bp.get("/")
def dashboard_page():
    payload = _build_dashboard_summary()
    return render_template("index.html", **payload)


@dashboard_bp.get("/api/dashboard")
def dashboard_api():
    payload = _build_dashboard_summary()
    return jsonify(payload)
