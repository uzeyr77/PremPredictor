"""
Central configuration for the Flask application.

Environment variables:
  PLP_DB_PATH           Path to prem_data.db (default: prem_data.db next to cwd)
  FLASK_ENV             development | production
  FLASK_DEBUG           1 or 0
  PLP_DEFAULT_SIMULATIONS
                          Override simulation count for dashboard / APIs.
                          If unset: 2000 in development (snappier UI), 10000 in production.
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
    # Monte Carlo is CPU-heavy: 10k sims can take many minutes before the first byte
    # leaves the server. Use a lower default in development unless overridden.
    if os.getenv("PLP_DEFAULT_SIMULATIONS") is not None:
        default_simulations = int(os.environ["PLP_DEFAULT_SIMULATIONS"])
    elif flask_env == "production":
        default_simulations = 10_000
    else:
        default_simulations = 2_000
    raw_seed = os.getenv("PLP_DEFAULT_SEED")
    default_seed = int(raw_seed) if raw_seed is not None else None

    return AppConfig(
        flask_env=flask_env,
        flask_debug=flask_debug,
        db_path=db_path,
        default_simulations=default_simulations,
        default_seed=default_seed,
    )
