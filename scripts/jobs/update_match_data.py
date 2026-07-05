import sqlite3
import requests
from datetime import datetime, timezone
conn = sqlite3.connect("../prem_data.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
API_KEY = 'b8148cbbfa334d1bb18ae21f5dfc2270'
URL = "https://api.football-data.org/v4/competitions/PL/matches?season=2025"
utc_now = datetime.now(timezone.utc)
headers = {
    'X-Auth-Token': API_KEY
}
TEAM_NAME_MAP = {
    'Brighton Hove': 'Brighton',
    'Wolverhampton': 'Wolves',
    'Nottingham': 'Nottm Forest',
    'Leeds United': 'Leeds',
    'Liverpool': 'Liverpool',
    'Burnley': 'Burnley',
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
    'West Ham': 'West Ham',
    'Man United': 'Man United'




}
match_records = []
try:
    response = requests.get(url=URL, headers=headers)
    data = response.json()
    for match in data.get('matches', []):
        is_played = match.get("status") == 'FINISHED'
        if is_played:
            # print(match)
            record = {
                "season": '2025',
                "matchweek": match.get("matchday", {}),
                "date": match.get("utcDate", {}),
                "home_team": TEAM_NAME_MAP.get(match.get('homeTeam').get('shortName', None)),
                "away_team": TEAM_NAME_MAP.get(match.get('awayTeam').get('shortName', None)),
                "home_goals": match.get('score', {}).get('fullTime', {}).get('home', None),
                "away_goals": match.get('score', {}).get('fullTime', {}).get('away', None),
                "played": 1
            }
            match_records.append(record)
    print(match_records)
except requests.exceptions.RequestException as e:
    print(f"error fetching data from api {e}")



# update the table where the field played == 1
for record in match_records:
    cursor.execute("""
        UPDATE match_data
        SET
            home_goals = ?,
            away_goals = ?,
            played = ?
        WHERE
            season = ? 
            AND matchweek = ?
            AND home_team = ?
            AND away_team = ?
            AND played = 0
    """,(
        int(record['home_goals']),
        int(record['away_goals']),
        int(record['played']),
        "2025",
        int(record["matchweek"]),
        record["home_team"],
        record["away_team"],
    ))

conn.commit()
conn.close()
print("updated db")



