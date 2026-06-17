import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config import load_config
from services.repository import PredictionRepository
from services.prediction_service import PredictionService
cfg = load_config()
repo = PredictionRepository(db_path = cfg.db_path)
repo.ensure_cache_schema()

service = PredictionService(repository = repo, config=cfg)
payload = service.get_dashboard_summary()
fp = repo.db_fingerprint()










