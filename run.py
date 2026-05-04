"""
Development entrypoint for the Premier League Predictor web app.

Run from project root:
  python run.py
"""

from app_factory import create_app


app = create_app()


if __name__ == "__main__":
    cfg = app.config["APP_CONFIG"]
    app.run(host="0.0.0.0", port=5000, debug=cfg.flask_debug)
