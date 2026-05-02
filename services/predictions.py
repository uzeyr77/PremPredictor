import pandas as pd
from flask import Flask, render_template
import sqlite3
import numpy as np
from pandas.core.interchange.dataframe_protocol import DataFrame
from scipy import stats
from scipy.stats import poisson
from sklearn.metrics import mean_absolute_error

# set up connection and query database
conn = sqlite3.connect("C:/Users/uzeyr/PremierLeaguePredictor/prem_data.db")
league_table = pd.read_sql_query("SELECT * FROM league_table_2025",conn)
league_table_2024_true = pd.read_sql_query("SELECT * FROM league_table_2024_final",conn)

matches = pd.read_sql_query("SELECT * FROM match_data",conn)
team_stats_2024 = pd.read_sql_query("SELECT * FROM prem_teams_2024", conn)
team_statistics = pd.read_sql_query("SELECT * FROM prem_teams_2025", conn)


# add column for league table for goal difference
if "goal_difference" not in league_table.columns:
    league_table["goal_difference"] = league_table["goals_for"] - league_table["goals_against"]

# constants for predictions
HOME_ADVANTAGE = 1.3
LEAGUE_AVERAGE_GOALS = 1.4
HOME_ADVANTAGE_2024 = 1.0648
LEAGUE_AVERAGE_GOALS_2024 = 1.467


# main predicition algorithm

def get_current_table() -> DataFrame:
    return league_table

def get_final_table() -> DataFrame:
    '''Returns the final table after the end of the season based on projected final points'''
    df_projected_points = get_project_final_points()
    curr_points = pd.DataFrame({'team': league_table['team'], 'points': league_table['points']})
    df_projected_table = curr_points.merge(df_projected_points)
    return df_projected_table
    
   
# wrapper to return the top 4 from predicitions
def get_top_4_race() -> DataFrame:
    '''
    function to get the top 4 teams in the league from predictions
    Returns: dataframe of the final table with only top 4 teams

    '''
    final_table = get_final_table()
    
    return final_table.head(4)

# wrapper to return the top 2 favourities from predicitions
def get_title_race() -> DataFrame:
    '''returns the top 2 teams of the table'''
    final_table = get_final_table()
    
    return final_table.head(2)
    
# helper functions
def get_actual_ppg() -> DataFrame:

    '''
    Function to get the true points per game of each team and returns a dataframe
    Pointer per game for team x is given by points(x)/games_played(x)
    Returns: a dataframe with the columns team and actual_ppg

    '''
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
    '''args: dataframe representing the goal difference of each team
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
    Blended_ppg = ppg_true * .30 + ppg_expected * .70
    Returns: a dataframe that contains every team and their blended ppg

    '''
    actual_ppg = get_actual_ppg()
    expected_ppg = get_expected_ppg()
    blended_ppg = actual_ppg['actual_ppg'].values* .70 + expected_ppg['expected_ppg'].values * .30
    df_blended_ppg = pd.DataFrame({'team': expected_ppg['team'].values, 'blended_ppg': blended_ppg})
    
    return df_blended_ppg

def get_project_final_points() -> DataFrame:
    # projected final points = current_points + (blended_ppg * games remaining)

    '''
    Function that takes the current points of each team, blended ppg and calculates the projected final points
    blended_ppg = ppg_true * .30 + ppg_expected * .70
    Projected_final_points = current_points + blended_ppg * games_left
    Returns: a dataframe with projected league table based on the current points from games played and a ppg based on teams performance this season
    Dataframe with columns [team, projected_final_points, position]
    return:     Dataframe with columns [team, projected_final_points, position]
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
    poisson.pmf(k, lambda): k represents the number of occurrences for some event, and lambda is expected(mean) number of occurrences
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
    Predict all unplayed fixtures for current season. Calls predict_match(home_team, away_team) which returns a percentage representing the probability of a draw, win, or a loss
    as well as expected goals from each
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
   process: call predict_mall_remaining the remaining fixtures (games in the matches db with played == 0), which returns a dataframe containing all the matches and the probability of a win, loss, or draw
   then with a loop and using npmy library a win, loss or draw is randomly selected for each match fixture and depending on which was chosen points are awarded accordingly
   (e.i if its a home win then home team gets 3 points and away team gets none) 
   this process repeats for all the remaining fixtures and each time starts off with current league points table --> predicts remaining matches and tally points --> add them to the current points table
   
   for each of the n simulations the outcomes for every team is tallied up. For each team tally this after every sim
   - league wins count
   - top 4 finishes count
   - relegated count
   - and every single point recorded for every season so if arsenal got 87, then 85, 84, 82 ... n that gets stored in a dictionary with (team, list(all_points)]
    Args:
        n_simulations: an integer for number of simulations to run

    Returns: {
         'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'all_simulations': all_simulations,
        'points_distribution': points_distribution
        }

    '''
    title_wins = {team: 0 for team in league_table['team']}
    top_4_finishes = {team: 0 for team in league_table['team']}
    top_2_finishes = {team: 0 for team in league_table['team']}
    relegation_finishes = {team: 0 for team in league_table['team']}
    all_simulations = []

    current_points = league_table[['team', 'points']].set_index('team')
    
    remaining_fixtures = predict_all_remaining_matches()
    teams = league_table['team'].tolist()
    points_distribution = {team: [] for team in teams}
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
        for i in range(2):
            top_2_finishes[sorted_teams.index[i]] += 1
        for i in range(-3, 0):  # Bottom 3
            relegation_finishes[sorted_teams.index[i]] += 1

        # get every tally of points for each sim and store in array
        for team, row in sim_points.iterrows():
            points = row['points']
            points_distribution[team].append(int(points))

        all_simulations.append(sim_points.copy())
        title_probs = {team: wins/n_simulations for team, wins in title_wins.items()}
        top_4_probs = {team: finishes/n_simulations for team, finishes in top_4_finishes.items()}
        top_2_probs = {team: finishes/n_simulations for team, finishes in top_2_finishes.items()}
        relegation_probs = {team: finishes/n_simulations for team, finishes in relegation_finishes.items()}
    return {
        'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'top_2_probabilities': top_2_probs,
        'all_simulations': all_simulations,
        'points_distribution': points_distribution
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
        'points_distribution': points_distribution
        }

    '''
    title_wins = {team: 0 for team in league_table['team']}
    top_4_finishes = {team: 0 for team in league_table['team']}
    relegation_finishes = {team: 0 for team in league_table['team']}
    all_simulations = []

    current_points = league_table[['team', 'points']].set_index('team')
    remaining_fixtures = fixtures
    teams = league_table['team'].tolist()
    points_distribution = {team: [] for team in teams}

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
            points_distribution[team].append(int(points))

        all_simulations.append(sim_points.copy())
        title_probs = {team: wins/n_simulations for team, wins in title_wins.items()}
        top_4_probs = {team: finishes/n_simulations for team, finishes in top_4_finishes.items()}
        relegation_probs = {team: finishes/n_simulations for team, finishes in relegation_finishes.items()}
    return {
        'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'all_simulations': all_simulations,
        'points_distribution': points_distribution
    }



def get_team_points_distribution(team:str, points_distribution: dict):

    '''
    Get points distribution of the final points for a specific team

    Args:
        team: some team in the pr
        points_distribution: a dict containing the team as the key and the points distribution for some n simulations
        e.i { "arsenal": [87, 83, 83 ... n], "man city": [..]

    Returns:   dict: {
            'min': 75,
            'max': 95,
            'median': 85,
            'p5': 78,   # 5th percentile
            'p95': 91,  # 95th percentile
            'points_distribution': [85, 86, 83, ...]  # For histogram
        }

    '''
    return {
        'min': min(points_distribution),
        'max': max(points_distribution),
        'median': np.median(points_distribution),
        'p5': np.percentile(points_distribution,5),
        'p95': np.percentile(points_distribution, 95),
        'points_distribution': points_distribution
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
    baseline_prob = baseline_results[prob_key]
    scenario_prob = scenario_results[prob_key]

    # build dataframe for comp
    comparison = []

    for team in baseline_prob.keys():
        baseline_prob = baseline_prob[team]
        scenario_prob = scenario_prob[team]
        change = scenario_prob - baseline_prob

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
    df_result['abs_change'] = df_result['change'].abs()
    df_result.sort_values(df_result['abs_change'], ascending= False).drop('abs_change')
    df_result.reset_index(drop = True)

    return df_result


def get_team_probabilities(n_simulations):

    resu = simulate_season(n_simulations)
    all_team_summary = {}
    for team in league_table["team"]:
        team_summary = {
            "team": team,
            "title_probability": resu["title_probabilities"][team],
            "top_2_probabilities": resu["top_2_probabilities"][team],
            "top_4_probability": resu["top_4_probabilities"][team],
            "relegation_probabilities": resu["relegation_probabilities"][team]


        }
        all_team_summary[team] = team_summary

    return all_team_summary


def predict_match_backtest(home_team: str, away_team: str, team_data: DataFrame) -> DataFrame:
    #  expected goals are the lambda values for each team
    #  poisson.pmf(k, Lambda) k represents the number of events (goals) and lambda is expected
    #  poisson.pmf(2, 1.6) is the probability of scoring EXACTLY 2 goals when the expected is 1.6

    '''
    poisson.pmf(k, lambda): k represents the number of occurances for some event, and lambda is expected(mean) number of occurances
    so it returns the probability of that event happening k times
    Args:
        team_data: the statistics for that season (e.i attack_strength, defense_strength)
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
    home_attack = team_data.loc[team_data['team'] == home_team, 'attack_strength'].values[0]
    home_defense = team_data.loc[team_data['team'] == home_team, 'defense_strength'].values[0]
    away_attack = team_data.loc[team_data['team'] == away_team, 'attack_strength'].values[0]
    away_defense = team_data.loc[team_data['team'] == away_team, 'defense_strength'].values[0]
    exp_home_goals = home_attack * away_defense * LEAGUE_AVERAGE_GOALS_2024 * HOME_ADVANTAGE_2024
    exp_away_goals = away_attack * home_defense * LEAGUE_AVERAGE_GOALS_2024
    home_win_prob = 0
    draw_prob = 0
    away_win_prob = 0
    prob = 0

    for home_score in range(0, 20):
        for away_score in range(0, 20):
            prob = poisson.pmf(home_score, exp_home_goals) * poisson.pmf(away_score, exp_away_goals)
            # calculate the probabilites for each scoreline
            if home_score > away_score:
                home_win_prob += prob
            elif away_score > home_score:
                away_win_prob += prob
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
def predict_all_remaining_matches_backtest(remaining_matches: DataFrame) -> DataFrame:
    """
    Predict all unplayed fixtures for current season
    remaining_matches: a dataframe containing the matches to predict the outcome of
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
    remaining_matches = remaining_matches
    predicted_rows = []
    for index in remaining_matches.index:  # loop through indices
        match = remaining_matches.loc[index]  # match is the ith row in the column
        home_t = match['home_team']
        away_t = match['away_team']
        match_prediction = predict_match_backtest(home_t, away_t, team_stats_2024)
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
def simulate_season_from_snapshot(snapshot_table: DataFrame, remaining_matches: DataFrame, team_stats: DataFrame, n_simulations: int) -> dict:
    '''
    With the data from a specific season, build on the current table (table_snapshot) by predicting what will happen for
    the remaining matches using the team_stats which has data like attack_strength defense_strength etc

    Args:
        snapshot_table: snapshot of how the table looks at some matchweek in a past season (e.i matchweek 14 of 2023-2024 season)
        remaining_matches: a table containing the remaining matches of some matchweek
        team_stats: the datapoints for each team, like attack strength, defense strength
        n_simulations: number of simulations to run

    Returns: a dictionary representing probabilities for title, top4, releg. and some other data
    e.i title_probs is a dict with each team and their probabilities of winning the title
    '''



    title_wins = {team: 0 for team in snapshot_table['team']}
    top_4_finishes = {team: 0 for team in snapshot_table['team']}
    top_2_finishes = {team: 0 for team in snapshot_table['team']}
    relegation_finishes = {team: 0 for team in snapshot_table['team']}
    all_simulations = []
    final_table = pd.DataFrame()

    current_points = snapshot_table[['team', 'points']].set_index('team')
    teams = snapshot_table['team'].tolist()
    remaining_fixtures = predict_all_remaining_matches_backtest(remaining_matches)
    points_distribution = {team: [] for team in teams}

    # print(current_points)
    sim_points = current_points.copy()
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
                sim_points.at[home, 'points'] += 1
                sim_points.at[away, 'points'] += 1
                # print(f"draw: {sim_points.at[home, 'points']}")
            else:  # away_win
                sim_points.at[away, 'points'] += 3
                # print(f"home loss: {sim_points.at[home, 'points']}")

        # sort the table by points
        sorted_teams = sim_points.sort_values(by='points', ascending=False)

        # Record outcomes
        title_wins[sorted_teams.index[0]] += 1  # Winner
        for i in range(4):  # Top 4
            top_4_finishes[sorted_teams.index[i]] += 1
        for i in range(2):
            top_2_finishes[sorted_teams.index[i]] += 1
        for i in range(-3, 0):  # Bottom 3
            relegation_finishes[sorted_teams.index[i]] += 1

        # get every tally of points for each sim and store in array
        for team, row in sim_points.iterrows():
            points = row['points']
            points_distribution[team].append(int(points))

        all_simulations.append(sim_points.copy())
        title_probs = {team: wins / n_simulations for team, wins in title_wins.items()}
        top_4_probs = {team: finishes / n_simulations for team, finishes in top_4_finishes.items()}
        top_2_probs = {team: finishes / n_simulations for team, finishes in top_2_finishes.items()}
        relegation_probs = {team: finishes / n_simulations for team, finishes in relegation_finishes.items()}


    return {
        'title_probabilities': title_probs,
        'top_4_probabilities': top_4_probs,
        'relegation_probabilities': relegation_probs,
        'top_2_probabilities': top_2_probs,
        'all_simulations': all_simulations,
        'points_distribution': points_distribution
    }

def build_predicted_points_table_from_snapshot(season_simulation_past_season: dict, league_table_from_snapshot: DataFrame) -> DataFrame:
    '''
    ***FOR BACK TESTING FROM THE 2024 SEASON***


    Builds a table with columns [team, points] based on the data from the points_distribution_from_snapshot which is a dictionary that contains an entry with the team
    and every point recorded for each simulated season (e.i { "arsenal": [81, 82, ... ] "man city": [82, 83,...]

    Args:
        season_simulation_past_season: dict with the distribution from the monte carlo simulation
        league_table_from_snapshot: league table so far

    Returns:

    '''


    league_points_pred_2024 = pd.DataFrame({
        "team": league_table_from_snapshot["team"]
    }).set_index("team")

    points_distribution_from_simulated_season = season_simulation_past_season["points_distribution"]

    for team, points_distribution in points_distribution_from_simulated_season.items():
        team_points_distribution = get_team_points_distribution_for_backtest(team, points_distribution)
        league_points_pred_2024.loc[team, "points"] = int(team_points_distribution["median"])

        # league_points_pred.loc[team] = median_of_team_points
    return league_points_pred_2024


def build_table_backtest(match_data: DataFrame):
        '''

        Args:
            match_data: match_data from previous season up to some matchweek n containing date, hom team, away team, result etc.
            so basically the data of games so far

        Returns: snapshot of the league table based on those results from matchweek 0 to n
        '''
        # win, loss, or draw and points, goals Scored, goals Conceded
        teams = team_stats_2024["team"]
        # drop the first row "teams"
        teams = teams[teams != 'team']
        df_table = pd.DataFrame({
            "team": teams,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0
        })


        for _, row in match_data.iterrows():
            home = row["home_team"]
            away = row["away_team"]
            df_table.loc[df_table["team"] == home, "goals_for"] += row["home_goals"]
            df_table.loc[df_table["team"] == home, "played"] += 1
            df_table.loc[df_table["team"] == home, "goals_against"] += row["away_goals"]
            # df_table.loc[df_table["team"] == home, "goal_difference"] += (row["home_goals"] - row["away_goals"])

            df_table.loc[df_table["team"] == away, "goals_for"] += row["away_goals"]
            df_table.loc[df_table["team"] == away, "played"] += 1
            df_table.loc[df_table["team"] == away, "goals_against"] += row["home_goals"]
            # df_table.loc[df_table["team"] == away, "goal_difference"] += (row["away_goals"] - row["home_goals"])

            if row["home_goals"] > row["away_goals"]:
                df_table.loc[df_table["team"] == home, "points"] += 3
                df_table.loc[df_table["team"] == home, "wins"] += 1
                df_table.loc[df_table["team"] == away, "losses"] += 1
            elif row["away_goals"] > row["home_goals"]:
                df_table.loc[df_table["team"] == away, "points"] += 3
                df_table.loc[df_table["team"] == away, "wins"] += 1
                df_table.loc[df_table["team"] == home, "losses"] += 1
            else:
                df_table.loc[df_table["team"] == home, "points"] += 1
                df_table.loc[df_table["team"] == away, "points"] += 1
                df_table.loc[df_table["team"] == away, "draws"] += 1
                df_table.loc[df_table["team"] == home, "draws"] += 1


        df_table["goal_difference"] = df_table["goals_for"] - df_table["goals_against"]

        # sorting df returns a new df, sort by points, then goal difference, then goals scored by each team
        df_table = df_table.sort_values(
            by=["points", "goal_difference", "goals_for"],
            ascending=[False, False, False]
        ).reset_index(drop=True)

        return df_table
def get_team_points_distribution_for_backtest(team:str, points_distribution: dict):

    '''
    ***FOR BACKTEST FROM 2024 SEASON***


    Get points distribution of the final points for a specific team from the 2024 season

    Args:
        team: some team in the pr
        points_distribution: a dict containing the team as the key and the points distribution for some n simulations
        e.i { "arsenal": [87, 83, 83 ... n], "man city": [..]

    Returns:   dict: {
            'min': 75,
            'max': 95,
            'median': 85,
            'p5': 78,   # 5th percentile
            'p95': 91,  # 95th percentile
            'points_distribution': [85, 86, 83, ...]  # For histogram
        }

    '''
    return {
        'min': min(points_distribution),
        'max': max(points_distribution),
        'median': np.median(points_distribution),
        'p5': np.percentile(points_distribution,5),
        'p95': np.percentile(points_distribution, 95),
        'points_distribution': points_distribution
    }



def backtest_model(season: str, at_gameweek: int) -> dict:

    '''

    Args:
        season: a year in the form of a string e.i 2024, 2025
        at_gameweek: some game week 0 <= at_gameweek <= 38

    Returns: accuracy based on some metrics (e.i MAE)

    '''

    # load current season data from database and aggregate by matches so far and matches remaining
    df_season_data = pd.read_sql_query("SELECT * FROM match_data WHERE season=?", conn, params=("2024",))
    matches_so_far = df_season_data[df_season_data["matchweek"] <= at_gameweek]
    matches_remaining = df_season_data[df_season_data["matchweek"] > at_gameweek]

    # create the league table from the match data from databse (not predicting just using outcomes to show what the table looked like at matchweek x)
    # simulate the season based on the league table at matchweek x, remaining matches, and the team stats
    snapshot_of_table = build_table_backtest(matches_so_far)
    season_simulation_2024 = simulate_season_from_snapshot(snapshot_of_table, matches_remaining, team_stats_2024, 10_000) # returns the dict with title, top4, and releg. probabilites
    league_points_predicted_2024 = build_predicted_points_table_from_snapshot(season_simulation_2024, snapshot_of_table)

    # calculate the mae of points but first align the teams
    # create a table with just points and team from true dataframe and make the table be the index
    # before comparing points row by row to get the mae must align the rows
    league_points_true_2024 = league_table_2024_true[["team", "points"]].set_index('team')
    true, pred= league_points_true_2024.align(league_points_predicted_2024)
    mae_points = mean_absolute_error(pred["points"], true["points"])

    # calculate the += 1 values for the position of each team
    points_pred = league_points_predicted_2024["points"].values
    points_true = league_table_2024_true["points"].values
    pm1 = 0
    for i in range(len(points_true)):
        if abs(int(points_pred[i]) - int(points_true[i])) <=1:
            print(abs(int(points_pred[i]) - int(points_true[i])))
            pm1 += 1


    top_4_pred = list(league_points_predicted_2024.index[:4])
    top_4_true = league_table_2024_true["team"].head(4).values
    top4_hit_count = 1- len( set(top_4_pred) - set(top_4_true))/4

    winner_correct = league_points_predicted_2024.index[0] == league_table_2024_true.iat[0,0]

    # get the points distribution of each team
    # then based on the median points that will build league table (highest median points to lowest median points)
    # for the MAE use the mean of the points


    return {
        "season": season,
        "at_gameweek": at_gameweek,
        "metrics": {
            "mae_points": mae_points,
            "pm1": pm1,
            "top4_hit_count": float(top4_hit_count),
            "title_winner_correct": winner_correct,
        },
        "predicted_top4": list(league_points_predicted_2024.index[:4]),
        "actual_top4": list(league_table_2024_true["team"].head(4).values),
        "predicted_champion": league_points_predicted_2024.index[0],
        "actual_champion": league_table_2024_true.iat[0,0],
        "predicted_relegated": list(league_points_predicted_2024.index[-3:]),
        "actual_relegated": list(league_table_2024_true["team"].tail(3).values)
    }


def build_predicted_points_table() -> DataFrame:
    '''
    Generates a dataframe with columns [team, points] based on the team distribution, will utilize the median values to find accurate representation of points
    Call get_team_points_distribution(n_sims) where n_sims = 10_000 and then use the dictionary all_value which contains [team, all_points_from_n_simulations] to find the median
    
    Note: points based off the median 

    Returns: table with each team and their points 

    '''
    # set the indx of the dataframe as the teams
    league_points_pred = pd.DataFrame({
        "team": league_table["team"]
    }).set_index("team")
    points_distribution = simulate_season(10_000)["points_distribution"]
    
    for team, points_distribution in points_distribution.items():
        team_points_distribution = get_team_points_distribution(team, points_distribution)
        league_points_pred.loc[team, "points"] = team_points_distribution["median"]


        # league_points_pred.loc[team] = median_of_team_points
    return league_points_pred


def get_accuracy_trend(season: str, checkpoints: list[int]) -> list[dict]:
    '''
    Get a trend graph for the accuracy page by looping over game weeks in the list
    and calling backtest_model() on each of the checkpoints and return the output of backtest_model
    as a list
    Args:
        season: season to run backtest on
        checkpoints: a list of ints from 0 - 38 representing the game week to run the backtest on

    Returns:

    '''

    invalid_checkpoints = any(n < 0 for n in checkpoints)
    if invalid_checkpoints:
        raise ValueError(f"The game weeks: {checkpoints} are not valid")


    payload = []
    for game_week in checkpoints:
        resu = backtest_model("2024", game_week)
        payload.append(
            resu
        )


    return payload


def get_team_error_profile(season: str, at_gameweek: int) -> list[dict]:
    '''
    compares predicted vs actual points of each team
    returns the per team error rows
    e.i
    {
    "season": 2024,
    "gameweek": 25,
    "team": "Arsenal",
    "predicted_points": 76,
    "actual_points": 74,
    "points_error": 2,
    "predicted_position": 2,
    "actual_position": 2,
    "position_error": 0
  },
    Args:
        season: season to run test on
        at_gameweek: game week cut off

    Returns: a list containing each teams error profile

    '''
    # load current season data from database and aggregate by matches so far and matches remaining
    df_season_data = pd.read_sql_query("SELECT * FROM match_data WHERE season=?", conn, params=("2024",))
    matches_so_far = df_season_data[df_season_data["matchweek"] <= at_gameweek]
    matches_remaining = df_season_data[df_season_data["matchweek"] > at_gameweek]

    # create the league table from the match data from databse (not predicting just using outcomes to show what the table looked like at matchweek x)
    # simulate the season based on the league table at matchweek x, remaining matches, and the team stats
    snapshot_of_table = build_table_backtest(matches_so_far)
    season_simulation_2024 = simulate_season_from_snapshot(snapshot_of_table, matches_remaining, team_stats_2024,
                                                           10_000)  # returns the dict with title, top4, and releg. probabilites
    league_points_predicted_2024 = build_predicted_points_table_from_snapshot(season_simulation_2024, snapshot_of_table)
    league_points_true_2024 = league_table_2024_true[["team", "points"]].set_index('team')

    payload = []

    if at_gameweek < 0:
        raise ValueError(f"The game week: {at_gameweek} is not valid")

    for team, row in league_points_true_2024.iterrows():

        team_error_profile = {
            "season": season,
            "gameweek": at_gameweek,
            "team": team,
            "predicted_points": int(league_points_predicted_2024.loc[team,"points"]),
            "actual_points": league_points_true_2024.loc[team, "points"],
            "points_error": abs(int(league_points_predicted_2024.loc[team,"points"]) - int(league_points_true_2024.loc[team, "points"])),
            "predicted_position": league_points_predicted_2024.index.get_loc(team) + 1,
            "actual_position": league_points_true_2024.index.get_loc(team) + 1,
            "position_error": abs(league_points_predicted_2024.index.get_loc(team) - league_points_true_2024.index.get_loc(team))
        }

        payload.append(team_error_profile)


    return payload


def get_data_freshness_metadata() -> dict:


    return {
      "season": 2024,
      "data_as_of_date": "2025-05-25",
      "data_as_of_gameweek": 38,
      "played_matches": 380
    }



def main():

     print(get_team_error_profile("2024", 15))
    
if __name__ == "__main__":
    main()