# Premier League Predictor

A web application that predicts Premier League outcomes using Monte Carlo simulations and Poisson-based statistical modeling. Features a live dashboard with match predictions, title race probabilities, and interactive scenario analysis.

## Features

- **Match Predictions** - Win/Draw/Loss probabilities and expected goals for all fixtures
- **Season Simulations** - 10,000+ Monte Carlo simulations to forecast final standings
- **Title Race Tracker** - Real-time probability updates for title, top-4, and relegation battles
- **Scenario Analysis** - Test "what-if" scenarios by locking in match outcomes and re-running simulations
- **Team Insights** - Current form, upcoming fixtures, and probability trends for each team
- **Live Data Updates** - Automated data pipeline refreshes match results and predictions every 6 hours

## Technologies

- **Backend**: Python, Flask, PostgreSQL
- **Data Science**: NumPy, SciPy, pandas
- **Frontend**: Jinja2, Vanilla JavaScript, CSS
- **Data Pipeline**: GitHub Actions (automated updates from Football-Data.org API)
- **Deployment**: Railway/Render with PostgreSQL database

## How It Works

The application uses Poisson distributions to model goal-scoring based on team attack/defense strengths, then runs Monte Carlo simulations to generate probability distributions for all possible season outcomes. Data is automatically updated via scheduled GitHub Actions workflows.

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or SQLite for local development)
- Football-Data.org API key ([get one here](https://www.football-data.org/))

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/PremierLeaguePredictor.git
cd PremierLeaguePredictor

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your database credentials and API key

# Start the development server
python run.py
```

The application will be available at `http://localhost:5000`

### Environment Variables

Create a `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/prem_predictor

# API
FOOTBALL_DATA_API_KEY=your_api_key_here

# Application
PLP_CURRENT_SEASON=2026/27
PLP_DEFAULT_SIMULATIONS=10000
```

## Usage

### Web Dashboard

Visit `http://localhost:5000` to access:
- **Overview**: Current standings, title race probabilities, and featured matches
- **Scenarios**: Test what-if scenarios by setting match outcomes
- **Teams**: Individual team statistics and probability trends

### API Endpoints

```bash
# Get dashboard data
GET /api/dashboard

# Run scenario simulation
POST /api/scenario
{
  "fixtures": [
    {"home": "Arsenal", "away": "Liverpool", "result": "home"}
  ]
}
```

## Project Structure

```
PremierLeaguePredictor/
├── routes/              # Flask blueprints
├── services/            # Business logic and simulations
├── models/              # Data models
├── templates/           # HTML templates
├── static/              # CSS, JavaScript, team logos
├── scripts/jobs/        # Scheduled background jobs
├── .github/workflows/   # GitHub Actions for data updates
├── config.py            # Configuration
├── database.py          # Database connection
└── app_factory.py       # Flask app factory
```

## Deployment

The application is designed to run on platforms like Railway or Render with PostgreSQL.

**Requirements**:
- PostgreSQL database
- GitHub Actions secrets configured for scheduled jobs
- Gunicorn for production server

**Procfile**:
```
web: gunicorn 'app_factory:create_app()' --bind 0.0.0.0:$PORT
```

Scheduled GitHub Actions workflows automatically update match data every 6 hours and refresh predictions every hour.

## Acknowledgments

- [Football-Data.org](https://www.football-data.org/) - Match data API
- Premier League - Official competition data
- SciPy/NumPy - Statistical computing

---

## License

This project is for educational and portfolio purposes. Premier League is a registered trademark. Match data is sourced from Football-Data.org under their terms of use.
