"""
Flask application factory.

Why use factory pattern:
- Easier testing (create app instances with test configs).
- Cleaner dependency injection of services.
- Better scaling as project grows.
"""

from flask import Flask

from boilerplate.config import load_config
from boilerplate.routes.dashboard_routes import dashboard_bp
from boilerplate.routes.predictions_routes import predictions_bp
from boilerplate.routes.fixtures_routes import fixtures_bp
from boilerplate.routes.accuracy_routes import accuracy_bp
from boilerplate.services.prediction_service import PredictionService
from boilerplate.services.repository import PredictionRepository


def create_app() -> Flask:
    """
    Build Flask app and wire shared dependencies.
    """
    config = load_config()

    app = Flask(__name__, template_folder="../templates")
    app.config["APP_CONFIG"] = config

    # Dependency wiring:
    # Create repository once, then inject into service once.
    # Routes can read this through current_app config.
    repository = PredictionRepository(db_path=config.db_path)
    service = PredictionService(repository=repository)
    app.config["PREDICTION_SERVICE"] = service

    # Register route groups.
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(fixtures_bp)
    app.register_blueprint(accuracy_bp)

    return app

