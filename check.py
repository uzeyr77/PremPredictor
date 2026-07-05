import pandas as pd
from config import load_config
from services.repository import PredictionRepository
from services.prediction_service import PredictionService
from services.predictions import get_team_error_profile, build_predicted_points_table_from_snapshot, build_table_backtest, simulate_season_from_snapshot
from dotenv import load_dotenv


load_dotenv()
cfg = load_config()
repository = PredictionRepository()
service = PredictionService(repository=repository, config=cfg)


def main():
    print(service.get_dashboard_summary())
if __name__ == "__main__":
    main()
