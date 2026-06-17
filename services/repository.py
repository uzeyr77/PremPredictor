"""
Repository layer for all DB access.

Routes should NEVER query SQLite directly from blueprint handlers — use this layer or services.
"""

import json
import sqlite3
import pandas as pd
from contextlib import contextmanager
from typing import Iterator
from datetime import datetime, timezone


from models.contracts import  DashboardSummary


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
        required = {"league_table_2025", "match_data", "prem_teams_2025", "league_table_2024_final", "prem_teams_2024"}
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

    def get_team_stats_2024(self) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query("SELECT * FROM prem_teams_2024", conn)

    def get_league_table_2024(self) -> pd.DataFrame:
        with self._connect() as conn:
            return pd.read_sql_query("SELECT * FROM league_table_2024_final", conn)

    def get_matchweek(self) -> int:
        played = self.get_match_data()
        played = played[played['season'] == 2025]
        played = played[played['played'] == 1]
        if played.empty:
            return 1
        return int(played["matchweek"].max())

    def get_latest_upcoming_match(self):
        matches = self.get_match_data()

        return matches.tail(1)
    
    def ensure_cache_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                 CREATE TABLE IF NOT EXISTS cache_computed (
                     cache_key TEXT PRIMARY KEY,
                     fingerprint TEXT NOT NULL,
                     payload TEXT NOT NULL,
                     computed_at TEXT NOT NULL,
                     ttl_seconds INTEGER NOT NULL

                 )              
    """)
            conn.commit()
    
    def db_fingerprint(self) -> str:
        
        current_points_sum = self.get_current_table()['points'].sum()
        current_games_played = self.get_match_data()
        current_games_played = len(current_games_played[(current_games_played['season'] == 2025) & (current_games_played['played'] == 1)])
        
        return f"{current_games_played}:{current_points_sum}"
    
    def upsert_cache(self, cache_key: str, fingerprint:str, payload:DashboardSummary, ttl_seconds = 1800):
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("""INSERT into cache_computed (cache_key, fingerprint, payload, computed_at, ttl_seconds)
            Values (?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                fingerprint = excluded.fingerprint,
                payload = excluded.payload,
                computed_at = excluded.computed_at,
                ttl_seconds = excluded.ttl_seconds
            """,
            (cache_key, fingerprint, json.dumps(payload), now , ttl_seconds),
        )
            conn.commit()

    def get_cached_payload(self, cache_key:str) -> dict | None:
        if not cache_key:
            raise ValueError("the cache_key cannot be empty")
        query = "SELECT fingerprint, payload, computed_at, ttl_seconds FROM cache_computed WHERE cache_key = ?"
        with self._connect() as conn:
            row = conn.execute(query, (cache_key,)).fetchone()

            if row is None:
                return None
            else:
                return {
                    'fingerprint': row[0],
                    'payload': row[1],
                    'computed_at': row[2],
                    'ttl_seconds': row[3]
                }


