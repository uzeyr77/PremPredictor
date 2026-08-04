import json
import pandas as pd
from contextlib import contextmanager
from datetime import datetime, timezone

from database import get_db_connection, get_db_connection_string
from config import load_config
from models.contracts import DashboardSummary

_CURRENT_SEASON = load_config().current_season

class PredictionRepository:
    pass

    @contextmanager
    def _connect(self):
        conn = get_db_connection()
        try:
            yield conn
        finally:
            conn.close()

    def _get_connection_string(self):
        """Get connection string for pandas operations."""
        return get_db_connection_string()

    def assert_required_tables(self) -> None:
        required = {"league_table_2026", "match_data", "prem_teams_2026", "league_table_2024_final", "prem_teams_2024"}
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'; """)
                existing_tables = {row[0] for row in cursor.fetchall()}

                missing = required - existing_tables
                if missing:
                    raise ValueError(f"Missing required tables: {sorted(missing)}")

    def get_current_table(self) -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM league_table_2026", self._get_connection_string())

    def get_team_statistics(self) -> pd.DataFrame:
        team_stats = pd.read_sql_query("SELECT * FROM prem_teams_2026", self._get_connection_string())
        return team_stats.drop(columns=["goals_scored", "goals_conceded"])

    def get_match_data(self) -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM match_data", self._get_connection_string())

    def get_team_stats_2024(self) -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM prem_teams_2024", self._get_connection_string())

    def get_league_table_2024(self) -> pd.DataFrame:
        return pd.read_sql_query("SELECT * FROM league_table_2024_final", self._get_connection_string())

    def get_matchweek(self) -> int:
        played = self.get_match_data()
        played = played[played['season'].astype(int) == _CURRENT_SEASON]
        played = played[played['played'] == 1]
        if played.empty:
            return 1
        return int(played["matchweek"].max())

    def get_latest_upcoming_match(self):
        matches = self.get_match_data()

        return matches.tail(1)
    
    def ensure_cache_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS dashboard_cache (
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
        current_games_played = len(current_games_played[(current_games_played['season'].astype(int) == _CURRENT_SEASON) & (current_games_played['played'] == 1)])
        
        return f"{current_games_played}:{current_points_sum}"
    
    def upsert_cache(self, cache_key: str, fingerprint:str, payload:DashboardSummary, ttl_seconds = 1800):
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""INSERT into dashboard_cache (cache_key, fingerprint, payload, computed_at, ttl_seconds)
                Values (%s, %s, %s, %s, %s)
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
        query = """
                SELECT fingerprint, payload, computed_at, ttl_seconds 
                FROM dashboard_cache 
                WHERE cache_key = %s
                """
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (cache_key,))
                row = cursor.fetchone()

                if row is None:
                    return None
                else:
                    return {
                        'fingerprint': row[0],
                        'payload': row[1],
                        'computed_at': row[2],
                        'ttl_seconds': row[3]
                    }
    def quick_check(self):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), inet_server_addr();")
                print(cur.fetchone())

                cur.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_name = 'league_table_2026';
                """)
                print(cur.fetchall())

