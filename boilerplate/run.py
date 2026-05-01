"""
Run script for scaffold architecture.

Usage:
    python -m boilerplate.run
"""

from boilerplate.app_factory import create_app


app = create_app()


if __name__ == "__main__":
    config = app.config["APP_CONFIG"]
    app.run(host="0.0.0.0", port=5000, debug=config.flask_debug)

