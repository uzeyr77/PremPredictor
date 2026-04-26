import pandas as pd
import sqlite3
#load matches
conn = sqlite3.connect("C:/Users/uzeyr/PremierLeaguePredictor/prem_data.db")
cursor = conn.cursor()
matches = pd.read_sql("SELECT * FROM matches_updated WHERE season = 2025 AND played = 1", conn)
cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
# print(cursor.fetchall())
# prem_data.db
matches = matches.dropna(subset=["home_goals", "away_goals"])

# type check (make sure they are integers)
matches["home_goals"] = matches["home_goals"].astype(int)
matches["away_goals"] = matches["away_goals"].astype(int)
matches["played"] = matches["played"].astype(int)
# print(matches.dtypes)
matches["home_wins"] = matches["home_goals"] > matches["away_goals"]
matches["home_draws"] = matches["home_goals"] == matches["away_goals"] 

matches["away_wins"] = matches["away_goals"] > matches["home_goals"]
matches["away_draws"] = matches["away_goals"] == matches["home_goals"] 
# home stats 
home_stats = matches.groupby("home_team").agg(
    home_played = ("home_team", "count"),
    home_wins = ("home_wins", "sum"),
    home_draws = ("home_draws", "sum"),
    home_goals_for = ("home_goals", "sum"),
    home_goals_against = ("away_goals", "sum")    
)


# away stats
away_stats = matches.groupby("away_team").agg (
    away_played = ("away_team", "count"),
    away_wins = ("away_wins", "sum"),
    away_draws = ("away_draws", "sum"),
    away_goals_for = ("away_goals", "sum"),
    away_goals_against = ("home_goals", "sum")
)

#
table = home_stats.join(away_stats, how="outer").fillna(0)
table.index.name = "team"
table = table.reset_index()
table["played"] = table["home_played"] + table["away_played"]
table["wins"] = table["home_wins"] + table["away_wins"]
table["draws"] = table["home_draws"] + table["away_draws"]
table["losses"] = table["played"] - table["wins"]  - table["draws"]
table["goals_for"] = table["home_goals_for"] + table["away_goals_for"]
table["goals_against"] = table["home_goals_against"] + table["away_goals_for"]
table["goal_difference"] = table["goals_for"] - table["goals_against"]
table["points"] = table["wins"]*3 + table["draws"] # a win is 3 points and a draw is 1


# sorting based on points
table = table.sort_values(
    by=["points", "goal_difference", "goals_for"], # sort the table by points if equal then gd, if equal then goals_for
    ascending = False
)

print(table.index)
# # updating the prem_table

cursor.execute("DELETE FROM league_table_2025")

for _, row in table.iterrows():
    
    cursor.execute("""
                   
        INSERT INTO league_table_2025(team, played, wins, draws, losses, goals_for, goals_against, points)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
        row["team"],
        int(row["played"]),
        int(row["wins"]),
        int(row["draws"]),
        int(row["losses"]),
        int(row["goals_for"]),
        int(row["goals_against"]),
        int(row["points"]),
    )
    
     )
    
# sorting based on points
table = table.sort_values(
    by=["points", "goal_difference", "goals_for"], # sort the table by points if equal then gd, if equal then goals_for
    ascending = False
)

conn.commit()
conn.close()
print("update was successful")