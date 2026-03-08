from flask import Flask, render_template

app = Flask(__name__, template_folder="templates")

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/title")
def leagueTitle():
    return "title route"

@app.route('/top4')
def name(name):
    return "top4 route"

@app.route('/table')
def wagwan(greet):
    return "table render"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)