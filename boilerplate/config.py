"""
Central configuration for the new Flask architecture.

Why this file is necessary:
- Prevents hardcoded paths in service logic.
- Makes local/dev/prod settings explicit.
- Gives you one source of truth for runtime knobs.
"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    """
    Immutable app config object passed into services/routes.
    """

    flask_env: str
    flask_debug: bool
    db_path: str
    default_simulations: int
    default_seed: int | None


def load_config() -> AppConfig:
    """
    Read environment variables and build typed config.

    TODO:
    - Add stronger validation (e.g., path existence checks).
    - Optionally load from .env with python-dotenv.
    """

    flask_env = os.getenv("FLASK_ENV", "development")
    flask_debug = os.getenv("FLASK_DEBUG", "1") == "1"
    db_path = os.getenv("PLP_DB_PATH", "prem_data.db")
    default_simulations = int(os.getenv("PLP_DEFAULT_SIMULATIONS", "10000"))

    raw_seed = os.getenv("PLP_DEFAULT_SEED")
    default_seed = int(raw_seed) if raw_seed is not None else None

    return AppConfig(
        flask_env=flask_env,
        flask_debug=flask_debug,
        db_path=db_path,
        default_simulations=default_simulations,
        default_seed=default_seed,
    )

