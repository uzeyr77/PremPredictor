from services import data_handler
from flask import Flask, render_template, request
from services import predictions as pred
app = Flask(__name__, template_folder="templates")

@app.route('/')
def index():
    """
    landing page:
    should display all the information
    - league table
    - top 4 specifically
    - title race
    - relegation battle
    - golden boot (maybe)
    """
    league_table = pred.league_table.drop(columns= ['team_id'])
    league_table = league_table[["team", "played", "wins", "draws", "losses", "goals_for", "goals_against", "goal_difference", "points"]]
    columns = ["Team", "MP", "W", "D", "L", "GF", "GA", "GD", "PTS"]
    row_data = list(league_table.values.tolist())
    return render_template('index.html', columns = columns, row_data = row_data)

@app.route("/predictions")
def predictions():
    """
    should display predictions:
    - title race
    - top 4
    - who gets relagated
    - who wins golden boot
    etc
    """
    return render_template('predictions.html')

@app.route('/scenario')
def scenario():

    '''
    user can introduce some scenarios and then predictions will be made based on that match outcome
    e.i arsenal beating chelsea and city lossing against leeds
    Returns:

    '''
    return render_template('scenario.html')

@app.route('/golden_boot')
def golden_boot():
    """
    golden boot predicitions
    Returns:

    """
    return render_template('goldenboot.html')

@app.route('/accuracy')
def accuracy():

    return render_template('accuracy.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)