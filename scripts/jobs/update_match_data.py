"""
Sync match_data with the football-data.org API for the current season.

- Finished matches -> set home_goals / away_goals and played = 1
- New fixtures not yet in the table -> insert with played = 0
- Rescheduled fixtures -> refresh the stored kickoff date

Safe to run repeatedly (updates in place; no duplicate inserts).
Run manually or via Task Scheduler:
    python scripts/jobs/update_match_data.py
"""
import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests
from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

from database import get_db_connection
from config import load_config

SEASON = load_config().current_season
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
URL = f"https://api.football-data.org/v4/competitions/PL/matches?season={SEASON}"

# football-data.org shortName -> our DB team name
TEAM_NAME_MAP = {
    'Brighton Hove': 'Brighton',
    'Coventry City': 'Coventry City',
    'Nottingham': 'Nottm Forest',
    'Leeds United': 'Leeds',
    'Liverpool': 'Liverpool',
    'Ipswich Town': 'Ipswich Town',
    'Chelsea': 'Chelsea',
    'Everton': 'Everton',
    'Tottenham': 'Tottenham',
    'Bournemouth': 'Bournemouth',
    'Aston Villa': 'Aston Villa',
    'Man City': 'Man City',
    'Sunderland': 'Sunderland',
    'Brentford': 'Brentford',
    'Newcastle': 'Newcastle',
    'Arsenal': 'Arsenal',
    'Fulham': 'Fulham',
    'Crystal Palace': 'Crystal Palace',
    'Hull City': 'Hull City',
    'Man United': 'Man United',
}

# fetch matches frin aou
def fetch_matches() -> list[dict]:
    response = requests.get(url=URL, headers={'X-Auth-Token': API_KEY}, timeout=30)
    response.raise_for_status() # for bad http
    return response.json().get('matches', [])


# turn api json -> db record
def build_records(matches: list[dict]) -> list[dict]:
    records = []
    skipped = []
    for match in matches:
        home = TEAM_NAME_MAP.get(match['homeTeam'].get('shortName'))
        away = TEAM_NAME_MAP.get(match['awayTeam'].get('shortName'))
        if home is None or away is None:
            skipped.append((match['homeTeam'].get('shortName'), match['awayTeam'].get('shortName')))
            continue

        finished = match.get('status') == 'FINISHED'
        score = match.get('score', {}).get('fullTime', {})
        records.append({
            "season": str(SEASON),
            "matchweek": int(match["matchday"]),
            "date": str(match["utcDate"]),
            "home_team": home,
            "away_team": away,
            "home_goals": score.get('home') if finished else None,
            "away_goals": score.get('away') if finished else None,
            "played": 1 if finished else 0,
        })

    if skipped:
        print(f"WARNING: {len(skipped)} matches skipped (unmapped team names): {set(skipped)}")
    return records


def sync(records: list[dict]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    updated_results = 0
    updated_dates = 0
    inserted = 0

    try:
        for r in records:
            key = (r['season'], r['matchweek'], r['home_team'], r['away_team'])

            if r['played'] == 1:
                cursor.execute(
                    """
                    UPDATE match_data
                    SET home_goals = %s, away_goals = %s, played = 1, date = %s
                    WHERE season = %s AND matchweek = %s
                      AND home_team = %s AND away_team = %s
                      AND played = 0
                    """,
                    (r['home_goals'], r['away_goals'], r['date'], *key),
                )
                updated_results += cursor.rowcount
                if cursor.rowcount > 0:
                    continue

            # keep kickoff dates fresh for unplayed fixtures (rescheduling)
            cursor.execute(
                """
                UPDATE match_data
                SET date = %s
                WHERE season = %s AND matchweek = %s
                  AND home_team = %s AND away_team = %s
                  AND played = 0 AND date <> %s
                """,
                (r['date'], *key, r['date']),
            )
            updated_dates += cursor.rowcount

            # insert fixture if it does not exist at all
            cursor.execute(
                """
                SELECT 1 FROM match_data
                WHERE season = %s AND matchweek = %s
                  AND home_team = %s AND away_team = %s
                """,
                key,
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """
                    INSERT INTO match_data
                        (season, matchweek, date, home_team, away_team, home_goals, away_goals, played)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        r['season'], r['matchweek'], r['date'],
                        r['home_team'], r['away_team'],
                        r['home_goals'] if r['home_goals'] is not None else 0,
                        r['away_goals'] if r['away_goals'] is not None else 0,
                        r['played'],
                    ),
                )
                inserted += 1

        conn.commit()
        print(f"season {SEASON}: {updated_results} results recorded, "
              f"{updated_dates} kickoff dates refreshed, {inserted} fixtures inserted")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> None:
    matches = fetch_matches()
    print(f"API returned {len(matches)} matches for season {SEASON}")
    records = build_records(matches)
    sync(records)
    print("update_match_data complete")


if __name__ == "__main__":
    main()
