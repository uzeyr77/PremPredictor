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

    return app
