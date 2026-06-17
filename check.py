from dotenv import load_dotenv
load_dotenv()

from config import load_config
from services.repository import PredictionRepository
from services.prediction_service import PredictionService

cfg = load_config()
repository = PredictionRepository(cfg.db_path)
service = PredictionService(repository=repository)


def main():
   print()

if __name__ == "__main__":
    main()
