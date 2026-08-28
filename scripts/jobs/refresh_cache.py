"""
Recompute the dashboard payload and store it in the db

Run:
    python scripts/jobs/refresh_cache.py
"""
import sys
import time
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

from config import load_config
from services.repository import PredictionRepository
from services.prediction_service import PredictionService


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def main() -> int:
    started = time.perf_counter()
    log("refresh_cache starting")

    cfg = load_config()
    log(f"config: env={cfg.flask_env}, sims={cfg.default_simulations}, season={cfg.current_season}")

    repo = PredictionRepository()
    repo.ensure_cache_schema()

    service = PredictionService(repository=repo, config=cfg)

    fingerprint = repo.db_fingerprint()
    log(f"db fingerprint: {fingerprint}")

    # Force a fresh compute (do NOT go through get_dashboard_summary, which
    # returns early on a cache hit and would make this job a no-op).
    log("computing dashboard summary...")
    payload = service.compute_dashboard_summary(cfg.default_simulations, cfg.default_seed)

    repo.upsert_cache('dashboard', fingerprint, payload)
    elapsed = time.perf_counter() - started
    log(f"dashboard cache updated OK in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"FAILED: {type(e).__name__}: {e}")
        raise
