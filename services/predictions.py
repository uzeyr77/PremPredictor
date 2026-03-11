import pandas as pd
from flask import Flask, render_template
import sqlite3

conn = sqlite3.connect("C:/Users/uzeyr/PremierLeaguePredictor/prem_data.db")
leage_table = pd.read_sql_query("SELECT * FROM league_table_2025",conn)
matches = pd.read_sql_query("SELECT * FROM matches_24_25",conn)
team_statistics = pd.read_sql_query("SELECT * FROM prem_teams_2025", conn)

# main predicition algorithm
def predict_final_table():
    
    print("final table")
   
# wrapper to return the top 4 from predicitions
def get_top_4_race():
    print("predict top 4")


# wrapper to return the top 2 favourities from predicitions
def get_title_race():
    print("league race")
    
    
# compute the top 4 calculations
def calculate_top_4_probability():
    print("top 4")
    

def main():
    print(team_statistics)    
    
# helper functions
if __name__ == "__main__":
    main()