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
  PLP_CURRENT_SEASON    Active season year for predictions (default: 2026)
  PLP_CURRENT_SEASON_LABEL  Display label e.g. 2026/27 (default: 2026/27)
"""

from dataclasses import dataclass
import os
from dotenv import load_dotenv
load_dotenv() # load env variables into os.environ



@dataclass(frozen=True)
class AppConfig:
    flask_env: str
    flask_debug: bool
    db_path: str
    default_simulations: int
    default_seed: int | None
    default_gameweek_backtest: int
    default_season_backtest: str
    default_checkpoints: list[int]
    current_season: int
    current_season_label: str

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
        default_simulations = 10
    raw_seed = os.getenv("PLP_DEFAULT_SEED")
    default_seed = int(raw_seed) if raw_seed is not None else None
    current_season = int(os.getenv("PLP_CURRENT_SEASON", "2026"))
    current_season_label = os.getenv("PLP_CURRENT_SEASON_LABEL", "2026/27")

    return AppConfig(
        flask_env=flask_env,
        flask_debug=flask_debug,
        db_path=db_path,
        default_simulations=default_simulations,
        default_seed=default_seed,
        default_gameweek_backtest=17, # right in the middle of the season
        default_season_backtest="2024", # season to backtest on
        default_checkpoints = [5,10,15,20,25,35],
        current_season=current_season,
        current_season_label=current_season_label,
    )
