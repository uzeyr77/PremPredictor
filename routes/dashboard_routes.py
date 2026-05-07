"""
Dashboard routes (home page + JSON API for the same data).

This file defines a *Blueprint*: a bundle of URL rules you register once in
``app_factory.create_app()``. The blueprint name ``"dashboard"`` is the first
argument to ``Blueprint(...)``; Flask uses it to build endpoint names like
``"dashboard.dashboard_page"`` for ``url_for(...)``.

Two routes serve the *same underlying data* in two shapes:
  - HTML for browsers opening ``/``
  - JSON for scripts/tools opening ``/api/dashboard``

Both should call the same service method so numbers never disagree between
the page and the API.
"""

from __future__ import annotations

# Blueprint: factory that builds route objects; __name__ helps Flask locate resources.
# current_app: the Flask app handling *this* request (only valid inside a request).
# jsonify: turns a Python dict into an HTTP response with Content-Type: application/json.
# render_template: runs Jinja2 on an HTML file under templates/, returns HTML text.
from flask import Blueprint, current_app, jsonify, render_template

from routes.query_params import _seed_from_request, _simulations_from_request

# ---------------------------------------------------------------------------
# Blueprint instance
# ---------------------------------------------------------------------------
# First arg "dashboard" is the blueprint *name* (used in url_for("dashboard.xxx")).
# __name__ is this module's name ("routes.dashboard_routes"); Flask uses it internally.
dashboard_bp = Blueprint("dashboard", __name__) # initialize blueprint with namespace "dashboard"

# endpoint = route (the blueprint aka URL) + view function (aka logic)
# Every endpoint is tied to a function so the naming scheme for an endpoint is: blueprint_name>.<function_name>
# the decorator @<blueprint_name>.route(..) is used to bind a specific url to a function
# multiple routes (noted by .route) can bind to the same endpoint, so multiple urls --> one endpoint
# a route by definition is a mapping of a url --> function

def _build_dashboard_summary():
    """
    Shared steps for both the HTML page and the JSON API.

    This is not a Flask "route" — it is a plain Python helper. We keep it in
    this module so both ``dashboard_page`` and ``dashboard_api`` stay short
    and identical in logic.

    Order of operations (every dashboard-style route in your app can copy this):
      1. Pull shared objects off the app (service + config).
      2. Parse query parameters (with defaults from config).
      3. Call *one* service method.
      4. Return the payload dict (caller decides HTML vs JSON).

    Why ``current_app`` here is OK: this function is only called from view
    functions, which Flask runs inside an *application context* that has a
    real app attached. Never call this at import time.
    """
    # ``current_app`` is a proxy to the active Flask app for this request.
    # ``.config`` is a dict-like object; keys are set in app_factory.create_app().
    # "PREDICTION_SERVICE" holds the single PredictionService instance (DI pattern).
    service = current_app.config["PREDICTION_SERVICE"]

    # "APP_CONFIG" is your dataclass from config.load_config(): defaults, db path, etc.
    cfg = current_app.config["APP_CONFIG"]

    # Read ?simulations= and ?seed= or fall back to cfg.default_simulations / cfg.default_seed.
    # Helpers live in query_params.py; they may call abort(400) if the client sends garbage.
    simulations = _simulations_from_request(cfg.default_simulations)
    seed = _seed_from_request(cfg.default_seed)

    # The browser waits until this returns — large ``simulations`` means a long request.
    current_app.logger.info(
        "Dashboard: starting Monte Carlo (%s simulations). First load can take a while.",
        simulations,
    )

    # One service call — all Monte Carlo / table logic stays out of this file.
    return service.get_dashboard_summary(simulations, seed)


@dashboard_bp.get("/")
def dashboard_page():
    """
    Serve the dashboard as HTML (browser navigates to ``/``).

    Flask matches GET requests to path "/" and runs this function. The return
    value becomes the HTTP response body (here: HTML string).
    """
    # Same payload dict the API returns as JSON — keys match models.contracts.DashboardSummary.
    payload = _build_dashboard_summary()

    # ``**payload`` unpacks the dict into keyword arguments for the template:
    #   last_updated, simulation_count, title_favorites, top_4_race, projected_table
    # So in index.html you can write {{ last_updated }}, {% for row in projected_table %}, etc.
    return render_template("index.html", **payload)


@dashboard_bp.get("/api/dashboard")
def dashboard_api():
    """
    Serve the dashboard as JSON (e.g. fetch('/api/dashboard?simulations=5000')).

    Same computation as dashboard_page; only the response format differs.
    Optional query params: simulations, seed (see query_params.py).
    """
    payload = _build_dashboard_summary()

    # jsonify serializes dicts/lists/str/numbers to JSON. It also sets the right status (200).
    return jsonify(payload)
