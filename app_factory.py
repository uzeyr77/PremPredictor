from __future__ import annotations

import os
from datetime import datetime
from flask import Flask

from config import load_config
from routes.dashboard_routes import dashboard_bp
from routes.scenario_routes import scenario_bp
from routes.jobs_routes import jobs_bp
from services.prediction_service import PredictionService
from services.repository import PredictionRepository


def create_app() -> Flask:
    config = load_config()
    root = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, template_folder=os.path.join(root, "templates"))
    app.config["APP_CONFIG"] = config

    repository = PredictionRepository()
    service = PredictionService(repository=repository, config=config)
    app.config["PREDICTION_REPOSITORY"] = repository
    app.config["PREDICTION_SERVICE"] = service

    repository.ensure_cache_schema()

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(scenario_bp)
    app.register_blueprint(jobs_bp)

    @app.template_filter("friendly_date")
    def friendly_date(value: str) -> str:
        """Convert date string to 'Sat 15 Aug' format."""
        try:
            # Try ISO 8601 datetime format first (2026-08-22T14:00:00Z)
            if "T" in value:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                # Fall back to simple date format (2026-08-22)
                dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.strftime("%a %d %b")
        except (ValueError, TypeError, AttributeError):
            return value

    @app.template_filter("formatKickoff")
    def format_kickoff(value: str) -> str:
        """Format ISO timestamp to local kickoff time (e.g., '10:00 AM')."""
        try:
            if isinstance(value, str):
                # Parse ISO 8601 datetime (2026-09-12T14:00:00Z)
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(value, datetime):
                dt = value
            else:
                return value
            # Return time in 12-hour format with AM/PM (Windows-compatible)
            time_str = dt.strftime("%I:%M %p")
            # Remove leading zero from hour manually for cross-platform compatibility
            if time_str[0] == "0":
                time_str = time_str[1:]
            return time_str
        except (ValueError, TypeError, AttributeError):
            return value

    @app.template_filter("formatDayHeader")
    def format_day_header(value: str) -> str:
        """Format ISO timestamp to day header (e.g., 'Saturday, September 12')."""
        try:
            if isinstance(value, str):
                # Parse ISO 8601 datetime (2026-09-12T14:00:00Z)
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(value, datetime):
                dt = value
            else:
                return value
            # Return full weekday, month, day (Windows-compatible)
            day_str = dt.strftime("%A, %B %d")
            # Remove leading zero from day manually for cross-platform compatibility
            parts = day_str.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].startswith("0"):
                day_str = parts[0] + " " + parts[1].lstrip("0")
            return day_str
        except (ValueError, TypeError, AttributeError):
            return value

    return app
