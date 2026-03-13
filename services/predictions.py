import pandas as pd
from flask import Flask, render_template
import sqlite3

conn = sqlite3.connect("C:/Users/uzeyr/PremierLeaguePredictor/prem_data.db")
league_table = pd.read_sql_query("SELECT * FROM league_table_2025",conn)
matches = pd.read_sql_query("SELECT * FROM matches_24_25",conn)
team_statistics = pd.read_sql_query("SELECT * FROM prem_teams_2025", conn)

# main predicition algorithm
def predict_final_table():
    df_projected_points = get_project_final_points()
    curr_points = pd.DataFrame({'team': league_table['team'], 'points': league_table['points']})
    df_projected_table = curr_points.merge(df_projected_points)
    # position = pd.DataFrame('team': league_table['team'], 'projected_position')
    return df_projected_table
    
   
# wrapper to return the top 4 from predicitions
def get_top_4_race():
    print("predict top 4")


# wrapper to return the top 2 favourities from predicitions
def get_title_race():
    print("league race")
    
    
# compute the top 4 calculations
def calculate_top_4_probability():
    print("top 4")


# helper functions
def get_actual_ppg():
    ppg = pd.DataFrame({'team': league_table["team"], 'actual_ppg': league_table["points"] / league_table["played"]})
    return ppg

def get_expected_ppg():
    df_goal_difference = get_goal_difference()
    df_expected_ppg = goal_difference_to_expected_ppg(df_goal_difference)
    
    return df_expected_ppg

def get_goal_difference():
     # league average for goals scored and conceded is 1.4
    # goal difference is attack strng * leage avg - defense strng * league avg
    df_goal_difference = pd.DataFrame({'team': team_statistics["team"], 'goal_difference': team_statistics['attack_strength'] * 1.4 - team_statistics['defense_strength'] * 1.4})
    return df_goal_difference 

def goal_difference_to_expected_ppg(df_goal_difference):    
    def map_to_ppg(goal_diff):
        if goal_diff >= 1.0:
          return 2.5
        elif goal_diff >= 0.7:
          return 2.2
        elif goal_diff >= 0.4:
           return 1.9
        elif goal_diff >= 0.1:
           return 1.6
        elif goal_diff >= -0.2:
            return 1.3
        elif goal_diff >= -0.5:
            return 1.0
        elif goal_diff >= -0.8:
            return 0.7
        else:
            return 0.4
    df_expected_ppg = pd.DataFrame({'team': df_goal_difference['team'].values, 'expected_ppg': df_goal_difference['goal_difference'].apply(map_to_ppg)})
    return df_expected_ppg

def get_combined_ppg():
    blended_ppg = get_blended_ppg()
    actual_ppg = get_actual_ppg()
    expected_ppg = get_expected_ppg()
    combined_ppg = actual_ppg.merge(expected_ppg).merge(blended_ppg)
    return combined_ppg
    
    
def get_blended_ppg():
    # blended ppg formula: actual_ppg * .70 + expected_ppg * .30
    actual_ppg = get_actual_ppg()
    expected_ppg = get_expected_ppg()
    blended_ppg = actual_ppg['actual_ppg'].values* .70 + expected_ppg['expected_ppg'].values * .30
    df_blended_ppg = pd.DataFrame({'team': expected_ppg['team'].values, 'blended_ppg': blended_ppg})
    
    return df_blended_ppg

def get_project_final_points():
    # projected final points = current_points + (blended_ppg * games remaining)
    current_points = pd.Series(league_table['points'])
    blended_ppg = get_blended_ppg()['blended_ppg']
    games_left = pd.Series(38 - league_table['played'])
    resu = pd.DataFrame({'team': league_table['team'],'projected_final_points':round(current_points + (blended_ppg * games_left))})
    # projected_points = pd.Series(resu, name="projected_final_points")
    resu = resu.sort_values(by='projected_final_points', ascending=False)
    resu['position'] = resu.index + 1
    return resu

def main():
    actual_ppg = get_actual_ppg()
    expected_ppg = get_expected_ppg()
    print(predict_final_table())
    
    
    
if __name__ == "__main__":
    main()