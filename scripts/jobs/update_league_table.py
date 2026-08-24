import pandas as pd
import os
import sys
import requests
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
    
from database import get_db_connection
from config import load_config

import requests
from dotenv import load_dotenv


load_dotenv(_PROJECT_ROOT / ".env")


SEASON = load_config().current_season
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
URL = f"https://api.football-data.org/v4/competitions/PL/standings?season={SEASON}"


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


def fetch_standings():
    response = requests.get(url=URL, headers = {'X-Auth-Token': API_KEY}, timeout = 30)
    response.raise_for_status()
    standings = response.json().get('standings', [])[0]["table"]
    
    
    return standings

def build_records(standings:list):
    records = []
    skipped = []
    
    for entry in standings:
        # position = entry['position']
        team = TEAM_NAME_MAP.get(entry['team'].get('shortName'))
        played = entry['playedGames']
        points = entry['points']
        wins = entry['won']
        draws = entry['draw']
        losses = entry['lost']
        goals_for = entry['goalsFor']
        goals_against = entry['goalsAgainst']
        # goal_difference = entry['goalDifference']
        
        records.append(
            {
            'team': team,
            'played': played,
            'wins': wins,
            'draws':draws,
            'losses': losses,
            'goals_for': goals_for,
            'goals_against': goals_against,
            "points": points
            }
        )
        
    if skipped:
        print(f"WARNING: {len(skipped)} matches skipped (unmapped team names): {set(skipped)}")
    return records

def sync(records: list):
    conn = get_db_connection()
    cursor = conn.cursor()
    updated_rows = 0
    
    try:
        
        for r in records:  
            key = r['team']
            cursor.execute(
                """
                UPDATE league_table_2026
                    SET team = %s, played = %s, wins = %s, draws = %s, 
                    losses = %s, goals_for = %s, goals_against = %s, points = %s
                WHERE team = %s
                """, (r['team'], r['played'], r['wins'], r['draws'], r['losses'],
                      r['goals_for'], r['goals_against'], r['points'], key)
        
            )
            updated_rows = updated_rows + 1
            print(r['team'])
        records.sort(
            key=lambda r: (
                -r['points'],
                -(r['goals_for'] - r['goals_against']),
                -r['goals_for']
            )
        )
        conn.commit()
        
    except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()
    print(f"rows updated {updated_rows}")
    

def main():
    standings = fetch_standings()
    records = build_records(standings)
    sync(records)

if __name__ == "__main__":
    main()
    
    

    