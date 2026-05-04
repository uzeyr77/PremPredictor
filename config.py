"""
Central configuration for the Flask application.

Environment variables:
  PLP_DB_PATH           Path to prem_data.db (default: prem_data.db next to cwd)
  FLASK_ENV             development | production
  FLASK_DEBUG           1 or 0
  PLP_DEFAULT_SIMULATIONS
  PLP_DEFAULT_SEED      Optional int for reproducibility hooks
"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AppConfig:
    flask_env: str
    flask_debug: bool
    db_path: str
    default_simulations: int
    default_seed: int | None


def load_config() -> AppConfig:
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
