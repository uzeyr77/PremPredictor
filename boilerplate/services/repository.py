"""
Repository layer for all DB access.

Analogy:
- Service layer asks "what data do I need?"
- Repository answers "here is the data from storage."

Routes should NEVER query SQLite directly.
"""

import sqlite3
from contextlib import contextmanager
from hmac import new
from typing import Iterator
import pandas as pd

# from services.predictions import league_table


class PredictionRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def assert_required_tables(self) -> None:
        """
        Ensure required tables exist before running predictions.

        TODO:
        - Query sqlite_master and verify:
          league_table_2025, match_data, prem_teams_2025
        - Raise explicit exception if missing.
        """

        required = {"league_table_2025", "match_data", "prem_teams_2025"}
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type= 'table';")
            existing_tables = {row[0] for row in cursor.fetchall()}

            missing = required - existing_tables
            if missing:
                raise ValueError(f"Missing required tables: {sorted(missing)}")



    def get_current_table(self) -> pd.DataFrame:
        """
        Load current standings.
        """

        with self._connect() as conn:
            cursor = conn.cursor()
            current_table = pd.read_sql_query("SELECT * FROM league_table_2025", conn)
            return current_table

        # raise NotImplementedError("TODO: SELECT * FROM league_table_2025")

    def get_team_statistics(self) -> pd.DataFrame:
        """
        Load attack/defense strengths for teams.
        """

        with self._connect() as conn:
            cursor = conn.cursor()
            team_stats = pd.read_sql_query("SELECT * FROM prem_teams_2025", conn)
            # exclude the columns goals_scored and goals_conceded
            team_stats.drop(columns = ["goals_scored", "goals_conceded"])

            return team_stats

        raise NotImplementedError("TODO: SELECT * FROM prem_teams_2025")

    def get_match_data(self) -> pd.DataFrame:
        """
        Load fixture and result data.
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            match_data = pd.read_sql_query("SELECT * FROM match_data", conn)
            return match_data
        raise NotImplementedError("TODO: SELECT * FROM match_data")




if __name__ == "__main__":
    db = "C:/Users/uzeyr/PremierLeaguePredictor/prem_data.db"
    p = PredictionRepository(db)
    p.assert_required_tables()

