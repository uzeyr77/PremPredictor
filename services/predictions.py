import pandas as pd
from flask import Flask, render_template
import sqlite3
import numpy as np
from pandas.core.interchange.dataframe_protocol import DataFrame
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
    '''Returns the final table after the end of the season based on projected final points'''
    df_projected_points = get_project_final_points()
    curr_points = pd.DataFrame({'team': league_table['team'], 'points': league_table['points']})
    df_projected_table = curr_points.merge(df_projected_points)
    return df_projected_table
    
   
# wrapper to return the top 4 from predicitions
def get_top_4_race():
    '''returns the top 4 teams, live as it is no predicition'''
    final_table = get_final_table()
    
    return final_table.head(4)

# wrapper to return the top 2 favourities from predicitions
def get_title_race():
    '''returns a  the top 2 teams of the table'''
    final_table = get_final_table()
    
    return final_table.head(2)
    
# helper functions
def get_actual_ppg():
    '''returns a dataframe that has each team and their ppg'''
    ppg = pd.DataFrame({'team': league_table["team"], 'actual_ppg': league_table["points"] / league_table["played"]})
    return ppg

def get_expected_ppg():
    '''returns a dataframe for the expected points per game based on attack/defense strength'''
    df_goal_difference = get_goal_difference()
    df_expected_ppg = goal_difference_to_expected_ppg(df_goal_difference)
    
    return df_expected_ppg

def get_goal_difference():
    '''Leage average for goals scored and conceded is also 1.4, returns a dataframe for the goal differene of each team
    goal difference for any team is calculated by attack_strength * league_avg - defense_strength * league_avg'''
     # league average for goals scored and conceded is 1.4
    # goal difference is attack strng * leage avg - defense strng * league avg
    df_goal_difference = pd.DataFrame({'team': team_statistics["team"], 'goal_difference': team_statistics['attack_strength'] * 1.4 - team_statistics['defense_strength'] * 1.4})
    return df_goal_difference 

def goal_difference_to_expected_ppg(df_goal_difference):
    '''args: dataframe representing the goal difference of each tean
       takes the goal difference of each team and maps it to a expected points per game
       the higher the goal difference the greater the ppg
       e.i a team with higher goal difference will have a higher expected ppg against a team with a lower goal difference
       return: dataframe that represents each teams expected ppg'''
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
    '''
    Returns: a dataframe that has the details for every teams expected ppg and blended ppg

    '''
    actual_ppg = get_actual_ppg()
    expected_ppg = get_expected_ppg()
    blended_ppg = actual_ppg['actual_ppg'].values* .70 + expected_ppg['expected_ppg'].values * .30
    df_blended_ppg = pd.DataFrame({'team': expected_ppg['team'].values, 'blended_ppg': blended_ppg})
    
    return df_blended_ppg

def get_project_final_points():
    # projected final points = current_points + (blended_ppg * games remaining)

    '''

    Returns: a dataframe with projected league table based on the current points from games played and a ppg based on teams performance this season

    '''
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

    '''
    poisson.pmf(k, lambda): k represents the number of occurances for some event, and lambda is expected(mean) number of occurances
    so it returns the probability of that event happening k times
    Args:
        home_team: the home team of a match
        away_team: the away team of a match

    Returns: a dataframe that contains the data for the probability of each outcome
    - home_win prob
    - away_win prob
    - draw_prob
    as well as
    - exp_home_goals
    - exp_away_goals
    for each match

    '''
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
    '''
   simulates the season for n iterations (monte carlo sim)
    Args:
        n_simulations: an integer for number of simulations to run

    Returns: {
         'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'all_simulations': all_simulations,
        'all_values': all_values
        }

    '''
    title_wins = {team: 0 for team in league_table['team']}
    top_4_finishes = {team: 0 for team in league_table['team']}
    relegation_finishes = {team: 0 for team in league_table['team']}
    all_simulations = []

    current_points = league_table[['team', 'points']].set_index('team')
    remaining_fixtures = predict_all_remaining_matches()
    teams = league_table['team'].tolist()
    all_values = {team: [] for team in teams}
    # print(current_points)
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

        # get every tally of points for each sim and store in array
        for team, row in sim_points.iterrows():
            points = row['points']
            all_values[team].append(int(points))

        all_simulations.append(sim_points.copy())
        title_probs = {team: wins/n_simulations for team, wins in title_wins.items()}
        top_4_probs = {team: finishes/n_simulations for team, finishes in top_4_finishes.items()}
        relegation_probs = {team: finishes/n_simulations for team, finishes in relegation_finishes.items()}
    return {
        'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'all_simulations': all_simulations,
        'all_values': all_values
    }
# monte carlo simulation for the scenario based simulation, helper function, will not be called directly
def simulate_season_scenario(fixtures, n_simulations):
    '''
      simulates the season for n iterations (monte carlo sim) but based on specific scenario(s)
    Args:
        n_simulations: an integer for number of simulations to run
        fixtures: an array containing scenarios for matches that have yet to occur
        of the form:
        fixtures =
        {
            ["home_team": some_team, "away_team": some_team, "outcome": win | draw | loss]
        }

    Returns: the predicted final table if that scenario was to occur

     {
         'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'all_simulations': all_simulations,
        'all_values': all_values
        }

    '''
    title_wins = {team: 0 for team in league_table['team']}
    top_4_finishes = {team: 0 for team in league_table['team']}
    relegation_finishes = {team: 0 for team in league_table['team']}
    all_simulations = []

    current_points = league_table[['team', 'points']].set_index('team')
    remaining_fixtures = fixtures
    teams = league_table['team'].tolist()
    all_values = {team: [] for team in teams}

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

        # get every tally of points for each sim and store in array
        for team, row in sim_points.iterrows():
            points = row['points']
            all_values[team].append(int(points))

        all_simulations.append(sim_points.copy())
        title_probs = {team: wins/n_simulations for team, wins in title_wins.items()}
        top_4_probs = {team: finishes/n_simulations for team, finishes in top_4_finishes.items()}
        relegation_probs = {team: finishes/n_simulations for team, finishes in relegation_finishes.items()}
    return {
        'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'all_simulations': all_simulations,
        'all_values': all_values
    }



def get_points_distribution(team:str, all_simulations):

    '''
    Get points distribution of the final points for a specific team

    Args:
        team: some team in the pr
        all_simulations: dataframe containing outcomes of the monte carlo sim

    Returns:   dict: {
            'min': 75,
            'max': 95,
            'median': 85,
            'p5': 78,   # 5th percentile
            'p95': 91,  # 95th percentile
            'all_values': [85, 86, 83, ...]  # For histogram
        }

    '''
    points_distribution = all_simulations['all_values'][team]
    return {
        'min': min(points_distribution),
        'max': max(points_distribution),
        'median': np.median(points_distribution),
        'p5': np.percentile(points_distribution,5),
        'p95': np.percentile(points_distribution, 95),
        'all_values': points_distribution
    }


def simulate_scenario(fixture_overrides: list[dict], n_simulations=5000):
    """
    Simulate season with user-specified results

    Args:
        fixture_overrides (list): [
            {'home': 'Arsenal', 'away': 'Liverpool', 'result': 'home_win'},
            {'home': 'Man City', 'away': 'Chelsea', 'result': 'draw'}
        ]
        n_simulations (int): Number of simulations (fewer for speed)

    Returns:
        dict: Same format as simulate_season()
    """
    '''  
         so user specifies some fixture outcomes e.i city beats leeds to get 3 points, then simulating this scenario will return
         what the outcome of that win was (e.i does it push city to win the league). Will be based of current points
    '''

    # check if the fixtures given have already happened by looking through the matches dataframe
    all_remaining_matches = matches[matches['played'] == 0]
    all_remaining_matches = all_remaining_matches[["home_team", "away_team"]]

    # makes it so current points is a df that has 2 columns only, namly team name and points and the index is team
    current_points = league_table[['team', 'points']].set_index('team')

    for override in fixture_overrides:
        home_team = override['home']
        away_team = override['away']
        outcome = override['result']

        if outcome == 'home_win':
            current_points.at[home_team, 'points'] += 3
        elif outcome == 'away_win':
            current_points.at[away_team, 'points'] += 3
        else:
            current_points.at[home_team, 'points'] += 1
            current_points.at[away_team, 'points'] += 1

    # predict the rest of the fixtures not including the ones overridden
    all_fixtures = predict_all_remaining_matches()

    # create a set of the fixtures to override from the fixture_overrides passed
    # e.i before: [ {'home': man city, 'away': arsenal}, {...}, and so on change to --> set {(arsenal, man city), (..,..), ..}
    # this provides faster look up time
    override_set = {(f['home'], f['away']) for f in fixture_overrides}
    for home, away in override_set:
        exists =  ((all_remaining_matches['home_team'] == home) & (all_remaining_matches['away_team'] == away)).any()
        if not exists:
            raise ValueError("Fixture list contains match that already happened, cannot predict given scenario")

    # filtering by checking if the fixture is in fixture_override
    remaining_fixtures = all_fixtures[
        # run a function row by row: for each row x in the dataframe all_fixtures if the tuple (home_team, away_team)
        # is in the overrided set put True else put False, .apply() returns a series of [True, False, False, ... ]
        # the ~ negates it so if a fixture is overridden it becomes false else it becomes true
        # so this only keeps the fixtures that have not been overridden assigned to remaining_fixtures
        ~all_fixtures.apply(lambda x: (x['home_team'], x['away_team']) in override_set, axis = 1)
    ]


    # simualte season with the remaining fixtures (not including the first outcomes) default is 10_000 runs
    return simulate_season_scenario(remaining_fixtures, n_simulations)

def compare_scenario(baseline_results: dict, scenario_results: dict, metric: str) -> DataFrame:
    # compare baseline Vs scenario prediction results
    # return is based on metric e.i title, top4, relegation etc
    # returns a df sorted by biggest probability change

    # raise exception if metric is invalid, if dicts are missing info

    # map the metric given to the corresponding probability
    metric_map =  {
        "title": "title_probabilities",
        "top_4": "top_4_probabilities",
        "relegation": "relegation_probabilities"
    }

    # get the probability dict based on the metric
    prob_key = metric_map[metric]
    baseline_probs = baseline_results[prob_key]
    scenario_probs = scenario_results[prob_key]

    # build dataframe for comp
    comparison = []

    for team in baseline_probs.keys():
        baseline_prob = baseline_probs[team]
        scenario_prob = scenario_probs[team]
        change = scenario_probs - baseline_prob

        comparison.append(
            {
                'team': team,
                'baseline_prob': baseline_prob,
                'scenario_prob': scenario_prob,
                'change': change,
                "change_pct": change * 100
            }

        )

        df_result = pd.DataFrame(comparison)
        df_result['abs_change'] = abs(df_result['change'])
        df_result.sort_values(df_result['abs_change'], ascending= False).drop('abs_change', axis = 1)
        df_result.reset_index(drop = True)

        return df_result



    
def main():
    print(predict_match("Man City", "Arsenal"))


    
if __name__ == "__main__":
    main()