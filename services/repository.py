"""
Repository layer for all DB access.

Routes should NEVER query SQLite directly from blueprint handlers — use this layer or services.
"""

import sqlite3
from contextlib import contextmanager
from typing import Iterator

import pandas as pd


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
        required = {"league_table_2025", "match_data", "prem_teams_2025"}
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type= 'table';")
            existing_tables = {row[0] for row in cursor.fetchall()}

            missing = required - existing_tables
            if missing:
                raise ValueError(f"Missing required tables: {sorted(missing)}")

    def get_current_table(self) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query("SELECT * FROM league_table_2025", conn)

    def get_team_statistics(self) -> pd.DataFrame:
        with self._connect() as conn:
            team_stats = pd.read_sql_query("SELECT * FROM prem_teams_2025", conn)
            return team_stats.drop(columns=["goals_scored", "goals_conceded"])

    def get_match_data(self) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query("SELECT * FROM match_data", conn)
