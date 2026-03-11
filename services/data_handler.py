import pandas as pd
from flask import Flask, render_template
import sqlite3



def get_league_standing():
    conn = sqlite3.connect("C:/Users/uzeyr/PremierLeaguePredictor/prem_data.db")
    query = "SELECT * FROM league_table_2025"
    df = pd.read_sql_query(query, conn)
    df.sort_values("points", ascending=False)     
    
    league_table = df.to_dict('records')
    return league_table


def main():
    print("hello")
    print(get_league_standing())

if __name__ == "__main__":
    main()