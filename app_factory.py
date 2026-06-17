"""
Flask application factory.

Usage:
  export FLASK_APP=app_factory:create_app
  flask run

Or:
  python run.py
"""

from __future__ import annotations

import os

from flask import Flask

from config import load_config
from routes.accuracy_routes import accuracy_bp
from routes.dashboard_routes import dashboard_bp
from routes.fixtures_routes import fixtures_bp
from routes.predictions_routes import predictions_bp
from services.prediction_service import PredictionService
from services.repository import PredictionRepository


def create_app() -> Flask:
    # load config from config.py
    # contains db path, default values as well as other configs (debug mode)
    config = load_config()

    root = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, template_folder=os.path.join(root, "templates"))
    app.config["APP_CONFIG"] = config
    app.config['DB_PATH'] = config.db_path

    # init PredictionRepository and PredictionService objects for usage
    # to use the service layer methods/functions from app.config["Prediction_SERVICE"]
    repository = PredictionRepository(db_path=config.db_path)
    service = PredictionService(repository=repository, config = config)
    app.config["PREDICTION_SERVICE"] = service


    # setup cache
    repository.ensure_cache_schema()

    # register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(fixtures_bp)
    app.register_blueprint(accuracy_bp)

    return app
