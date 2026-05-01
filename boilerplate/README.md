# Boilerplate Package (Scaffold Only)

This folder is a **teaching scaffold**: file layout, function signatures, and comments.
Implementations are intentionally left as TODOs so you can build each part yourself.

## Why this exists

Your current project has working prediction logic, but a lot of logic is still coupled together.
This scaffold gives you a clean architecture to implement in steps without breaking your existing app.

## Folder overview

- `app_factory.py`: creates Flask app and registers route blueprints.
- `config.py`: central runtime configuration and env var parsing.
- `run.py`: entry-point to launch the scaffold app.
- `models/contracts.py`: typed payload contracts used by service and routes.
- `routes/`: page routes and JSON API routes.
- `services/`: repository, validation, config constants, orchestration service.
- `tests/`: test skeletons for service and route behavior.

## Recommended implementation order

1. `services/repository.py`
2. `services/validators.py`
3. `services/prediction_service.py`
4. `routes/*.py`
5. `tests/*`

## Important

- Do not duplicate prediction math in routes.
- Keep data access in repository layer.
- Keep route outputs consistent with contracts in `models/contracts.py`.

