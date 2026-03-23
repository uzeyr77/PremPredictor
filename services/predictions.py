import pandas as pd
from flask import Flask, render_template
import sqlite3
import numpy as np
from scipy import stats
from scipy.stats import poisson
conn = sqlite3.connect("C:/Users/uzeyr/PremierLeaguePredictor/prem_data.db")
league_table = pd.read_sql_query("SELECT * FROM league_table_2025",conn)
matches = pd.read_sql_query("SELECT * FROM match_data",conn)
team_statistics = pd.read_sql_query("SELECT * FROM prem_teams_2025", conn)
HOME_ADVANTAGE = 1.3
LEAGUE_AVERAGE_GOALS = 1.4
# main predicition algorithm
def get_final_table():
    df_projected_points = get_project_final_points()
    curr_points = pd.DataFrame({'team': league_table['team'], 'points': league_table['points']})
    df_projected_table = curr_points.merge(df_projected_points)
    return df_projected_table
    
   
# wrapper to return the top 4 from predicitions
def get_top_4_race():
    final_table = get_final_table()
    
    return final_table.head(4)

# wrapper to return the top 2 favourities from predicitions
def get_title_race():
    final_table = get_final_table()
    
    return final_table.head(2) 
    
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
    resu = resu.sort_values(by='projected_final_points', ascending=False)
    resu = resu.reset_index(drop=True) # makes sure that position matches up with the projected_final_points
    resu['position'] = resu.index + 1
    return resu


def predict_match(home_team:str,away_team:str):
    #  expected goals are the lambda values for each team
    #  poisson.pmf(k, Lambda) k represents the number of events (goals) and lambda is expected
    #  poisson.pmf(2, 1.6) is the probability of scoring EXACTLY 2 goals when the expected is 1.6
    home_attack =  team_statistics.loc[team_statistics['team'] == home_team, 'attack_strength'].values[0]
    home_defense = team_statistics.loc[team_statistics['team'] == home_team, 'defense_strength'].values[0] 
    away_attack =  team_statistics.loc[team_statistics['team'] == away_team, 'attack_strength'].values[0] 
    away_defense = team_statistics.loc[team_statistics['team'] == away_team, 'defense_strength'].values[0]
    exp_home_goals = home_attack * away_defense * LEAGUE_AVERAGE_GOALS * HOME_ADVANTAGE
    exp_away_goals =  away_attack * home_defense * LEAGUE_AVERAGE_GOALS
    home_win_prob = 0
    draw_prob = 0
    away_win_prob = 0
    prob = 0
    
    for home_score in range(0,20):
        for away_score in range(0,20):
            prob = poisson.pmf(home_score, exp_home_goals) *  poisson.pmf(away_score, exp_away_goals)
        # calculate the probabilites for each scoreline
            if home_score > away_score:
                home_win_prob += prob
            elif away_score > home_score:
                away_win_prob +=prob
            else:
                draw_prob += prob
            
    resu = {
        "home_win_prob": float(home_win_prob),
        "away_win_prob": float(away_win_prob),
        "draw_prob": float(draw_prob),
        "expected_home_goals": float(exp_home_goals),
        "expected_away_goals": float(exp_away_goals)
    }
    # print("home win:", home_win_prob)  
    # print("home win:", away_win_prob) 
    # print("draw prob:", draw_prob)       
    return resu

def predict_all_remaining_matches():
    """
    Predict all unplayed fixtures for current season
    Returns:
        DataFrame with columns:
        - date
        - home_team
        - away_team
        - home_win_prob
        - draw_prob
        - away_win_prob
        - expected_home_goals
        - expected_away_goals
    """
    remaining_matches = matches[matches['played'] == 0]
    predicted_rows = []
    for index in remaining_matches.index: # loop through indices
        match = remaining_matches.loc[index] # match is the ith row in the column
        home_t = match['home_team']
        away_t = match['away_team']
        match_prediction = predict_match(home_t, away_t)
        home_win_prob = match_prediction['home_win_prob']
        draw_prob = match_prediction['draw_prob']
        away_win_prob = match_prediction['away_win_prob']
        exp_home_goals = match_prediction['expected_home_goals']
        exp_away_goals = match_prediction['expected_away_goals']
        
        row = {
            'date': remaining_matches.at[index, 'date'],
            'home_team': home_t,
            'away_team': away_t,
            'home_win_prob': home_win_prob,
            'draw_prob': draw_prob,
            'away_win_prob': away_win_prob,
            'expected_home_goals': exp_home_goals,
            'expected_away_goals': exp_away_goals
        }
        
        predicted_rows.append(row)
        
    predicted_results = pd.DataFrame(predicted_rows)
    
    return predicted_results
        

def simulate_season(n_simulations):
    title_wins = {team: 0 for team in league_table['team']}
    top_4_finishes = {team: 0 for team in league_table['team']}
    relegation_finishes = {team: 0 for team in league_table['team']}
    all_simulations = []
    
    current_points = league_table[['team', 'points']].set_index('team')
    remaining_fixtures = predict_all_remaining_matches()
    
    for sim in range(n_simulations):
        sim_points = current_points.copy()
        if sim % 1000 == 0:
            print(f"Simulation {sim}/{n_simulations}")
    
        for _, match in remaining_fixtures.iterrows():
            home = match['home_team']
            away = match['away_team']
            probs = [match['home_win_prob'], match['draw_prob'], match['away_win_prob']]
            # print(f"{home} vs {away}: prob: {probs}\n")
            # Randomly sample outcome based on probabilities
            outcome = np.random.choice(['home_win', 'draw', 'away_win'], p=probs)
            # print(f"{outcome}\n")
            # Award points
            
            if outcome == 'home_win':
                sim_points.at[home, 'points'] += 3
                # print(f"home win : {sim_points.at[home, 'points']}")
            elif outcome == 'draw':
                sim_points.at[home, 'points']+= 1
                sim_points.at[away, 'points'] += 1
                # print(f"draw: {sim_points.at[home, 'points']}")
            else:  # away_win
                sim_points.at[away, 'points'] += 3
                # print(f"home loss: {sim_points.at[home, 'points']}")
        
    # Sort teams by points to get final table for this simulation
        sorted_teams = sim_points.sort_values(by = 'points', ascending=False)
        
        # Record outcomes
        title_wins[sorted_teams.index[0]] += 1  # Winner
        for i in range(4):  # Top 4
            top_4_finishes[sorted_teams.index[i]] += 1
        for i in range(-3, 0):  # Bottom 3
            relegation_finishes[sorted_teams.index[i]] += 1
        
        # Store full simulation result
        all_simulations.append(sim_points.copy())
        # Convert counts to probabilities
        title_probs = {team: wins/n_simulations for team, wins in title_wins.items()}
        top_4_probs = {team: finishes/n_simulations for team, finishes in top_4_finishes.items()}
        relegation_probs = {team: finishes/n_simulations for team, finishes in relegation_finishes.items()}

    return {
        'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'all_simulations': all_simulations
    }

    
    
def main():
    # actual_ppg = get_actual_ppg()
    # expected_ppg = get_expected_ppg()
    # print(get_final_table())
    # print("top two race:\n", get_title_race())
    # print("top 4 race:\n", get_top_4_race())
    result = simulate_season(1000)
    print("TITLE race: ", result['top_4_probabilities']) 
    
    
if __name__ == "__main__":
    main()