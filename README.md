# Premier League Predictor

A web application that predicts Premier League outcomes using Monte Carlo simulations and Poisson-based statistical modeling. Features a live dashboard with match predictions, title race probabilities, and interactive scenario analysis.

**Live Demo**: [https://prempredictor-pz93.onrender.com/](https://prempredictor-pz93.onrender.com/)

## Overview

This application combines statistical modeling with modern web development to deliver Premier League predictions through an intuitive dashboard. The system architecture emphasizes **performance** (intelligent caching), **reliability** (automated data pipelines), and **scalability** (managed cloud infrastructure).

**Key Highlights:**
- 🎯 **10,000+ Monte Carlo simulations** per prediction cycle
- ⚡ **Sub-50ms response times** via intelligent cache strategy
- 🤖 **Fully automated** data pipeline with GitHub Actions
- 🗄️ **Production-grade** database with Supabase PostgreSQL
- 🚀 **Zero-downtime deployments** on Render

## Table of Contents

- [Features](#features)
- [Technologies](#technologies)
- [How It Works](#how-it-works)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## Features

- **Match Predictions** - Win/Draw/Loss probabilities and expected goals for all fixtures
- **Season Simulations** - 10,000+ Monte Carlo simulations to forecast final standings
- **Title Race Tracker** - Real-time probability updates for title, top-4, and relegation battles
- **Scenario Analysis** - Test "what-if" scenarios by locking in match outcomes and re-running simulations
- **Team Insights** - Current form, upcoming fixtures, and probability trends for each team
- **Live Data Updates** - Automated data pipeline refreshes match results and predictions every 6 hours

## Technologies

### Backend
- **Framework**: Flask 3.1 with Blueprint architecture
- **Database**: Supabase (PostgreSQL)
- **Python Libraries**: NumPy, SciPy, pandas for statistical modeling

### Frontend
- **Templating**: Jinja2 (server-side rendering)
- **JavaScript**: Vanilla JS (no framework dependencies)
- **Styling**: Custom CSS with design token system

### Infrastructure
- **Hosting**: Render
- **Database**: Supabase (managed PostgreSQL)
- **CI/CD**: GitHub Actions for automated data updates
- **Data Source**: Football-Data.org API

### Automation
- **Scheduled Jobs**: GitHub Actions workflows
  - Match data updates every 6 hours
  - Prediction cache refresh every hour
  - Manual trigger support

## How It Works

The application uses Poisson distributions to model goal-scoring based on team attack/defense strengths, then runs Monte Carlo simulations to generate probability distributions for all possible season outcomes.

**Statistical Model:**
1. **Team Strength Calculation** - Compute attack/defense ratings from historical match data
2. **Expected Goals (xG)** - Poisson-based modeling for match outcome probabilities
3. **Monte Carlo Simulation** - Run 10,000+ season simulations to generate probability distributions
4. **Automated Updates** - GitHub Actions workflows refresh data every 6 hours

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Supabase account (or local PostgreSQL 14+)
- Football-Data.org API key ([get one here](https://www.football-data.org/))

### Local Development Setup

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

Create a `.env` file in the project root:

```env
# Supabase Database Connection
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres

# Football Data API
FOOTBALL_DATA_API_KEY=your_api_key_here

# Application Configuration
PLP_CURRENT_SEASON=2026/27
PLP_DEFAULT_SIMULATIONS=10000
SECRET_KEY=your-secret-key-here
```

**Supabase Setup:**
1. Create a new project in [Supabase](https://supabase.com/)
2. Go to Project Settings → Database
3. Copy the connection string (URI format)
4. Replace `[password]` with your database password

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

The application is deployed on **Render** with **Supabase** as the managed PostgreSQL database.

### Production Environment

**Live Application**: [https://prempredictor-pz93.onrender.com/](https://prempredictor-pz93.onrender.com/)

**Infrastructure:**
- **Web Service**: Render (with Gunicorn)
- **Database**: Supabase (managed PostgreSQL)
- **Background Jobs**: GitHub Actions (scheduled workflows)

### Deployment Configuration

**Render Setup:**
1. Create a new Web Service on [Render](https://render.com/)
2. Connect your GitHub repository
3. Configure build and start commands:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn 'app_factory:create_app()' --bind 0.0.0.0:$PORT`

**Environment Variables (Render):**
```
DATABASE_URL=<supabase-connection-string>
FOOTBALL_DATA_API_KEY=<your-api-key>
PLP_CURRENT_SEASON=2026/27
PLP_DEFAULT_SIMULATIONS=10000
SECRET_KEY=<production-secret-key>
```

**GitHub Actions Secrets:**

Configure these secrets in your repository for scheduled jobs:
- `DATABASE_URL` - Supabase connection string
- `FOOTBALL_DATA_API_KEY` - Football Data API key
- `PLP_CURRENT_SEASON` - Current season identifier
- `PLP_DEFAULT_SIMULATIONS` - Number of simulations (10000)

### Scheduled Jobs

GitHub Actions workflows run automatically:
- **Data Updates** (every 6 hours): Fetches latest match results and standings
- **Cache Refresh** (every hour): Regenerates prediction cache
- **Manual Triggers**: Available via GitHub Actions UI

### Database Schema

The application requires the following tables in Supabase:
- `matches` - Match results and fixtures
- `teams` - Team information and statistics
- `league_table` - Current standings
- `predictions_cache` - Pre-computed dashboard data

## Acknowledgments

- [Football-Data.org](https://www.football-data.org/) - Match data API provider
- [Supabase](https://supabase.com/) - Managed PostgreSQL database
- [Render](https://render.com/) - Web application hosting
- Premier League - Official competition data
- SciPy/NumPy - Statistical computing libraries

## License

This project is for educational and portfolio purposes. Premier League is a registered trademark. Match data is sourced from Football-Data.org under their terms of use.

---

**Built with Python, Flask, and Supabase • Deployed on Render • Automated with GitHub Actions**
