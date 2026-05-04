# Layout migration (boilerplate → project root)

The previous `boilerplate/` package was **merged into the repository root** so there is a **single** Flask-oriented tree next to the prediction **engine** (`services/predictions.py`).

## Current layout

| Path | Role |
|------|------|
| [`config.py`](../config.py) | Env-driven app configuration (`PLP_DB_PATH`, etc.) |
| [`app_factory.py`](../app_factory.py) | `create_app()` — registers blueprints and `PREDICTION_SERVICE` |
| [`run.py`](../run.py) | Dev server entry (`python run.py`) |
| [`routes/`](../routes/) | Flask blueprints (HTML + `/api/*` stubs until wired) |
| [`models/`](../models/) | Typed contracts (`DashboardSummary`, …) |
| [`services/prediction_service.py`](../services/prediction_service.py) | Orchestration for HTTP |
| [`services/repository.py`](../services/repository.py) | SQLite access (uses `config.db_path` for the **repository**; engine may still use its own path at import time) |
| [`services/validators.py`](../services/validators.py) | Input validation |
| [`services/predictions.py`](../services/predictions.py) | Monte Carlo engine + backtests |
| [`services/data_handler.py`](../services/data_handler.py) | Legacy helpers (optional cleanup later) |
| [`scripts/pl_predictor_cli.py`](../scripts/pl_predictor_cli.py) | Conversational CLI (`PYTHONPATH` = project root) |
| [`tests/`](../tests/) | Pytest (`pytest.ini` → `testpaths = tests`) |

## Commands

```powershell
# Web (from repo root)
python run.py

# Or Flask CLI
set FLASK_APP=app_factory:create_app
flask run

# Tests
python -m pytest tests -m "not integration"

# CLI
python scripts/pl_predictor_cli.py
```

## Removed

- **`boilerplate/`** package directory (deleted after migration).
- **Root `app.py`** — replaced by blueprint-based `create_app()` so routes are not duplicated.

## Imports

All internal imports use **project-root** packages: `from routes...`, `from services...`, `from models...` with `PYTHONPATH` = repo root (see [`pytest.ini`](../pytest.ini) and running from the project directory).
