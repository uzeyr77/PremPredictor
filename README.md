# Premier League Predictor

A statistical modeling tool that predicts Premier League outcomes using Poisson-based match simulations and Monte Carlo methods.

Built to apply probability, data analysis, and simulation to something real: football.

---

## Overview

The league table shows what has happened. This project focuses on what is likely to happen next.

Using two seasons of Premier League data stored in SQLite, the model:

* Estimates expected goals from team attack and defense strength
* Simulates thousands of matches and full seasons
* Outputs probabilities for titles, top-4 finishes, and relegation

It also supports match predictions and scenario analysis through a conversational CLI.

---

## Key Features

**Match Prediction**
Poisson-based goal modeling that produces win, draw, and loss probabilities.

**Monte Carlo Simulation**
10,000+ simulated seasons to generate outcome distributions.

**Projected Table**
Blended points-per-game model (70% actual, 30% expected).

**Scenario Analysis**
Lock in specific results and re-simulate the season.

**Conversational CLI**
Ask questions naturally with fuzzy team name matching. No memorizing commands.

**Team Insights**
Current form, projected points, and probability breakdowns.

---

## How It Works

* Load match and team data from SQLite into pandas
* Compute expected goals using attack and defense ratings
* Model scoreline probabilities using a Poisson distribution
* Resolve remaining fixtures with weighted random sampling
* Aggregate points into a final table
* Repeat thousands of times to build probability distributions

---

## The CLI

This is not a traditional command-line tool. It understands natural language and responds conversationally.

### Example Usage

```
You > Show me the table
You > Predict arsenal vs liverpool
You > What are the title race odds?
You > How's Arsenal doing?
You > What if Man City beats Chelsea?
```

### What Makes It Different

Traditional CLI tools require exact commands and strict syntax. This CLI allows free-form input and interprets user intent automatically.

---

## How the CLI Works

### 1. Intent Recognition

The system analyzes the user's input and determines what they want.

Example:

* Input: "what are arsenal's chances of winning the title?"
* Intent: title race
* Extracted team: Arsenal

### 2. Entity Extraction

The CLI automatically extracts useful information from text:

* Team names
* Number of simulations
* Match pairings

Example:

* Input: "predict arsenal vs liverpool with 5000 simulations"
* Teams: Arsenal, Liverpool
* Simulations: 5000

### 3. Fuzzy Matching

Handles typos and partial names:

* "ars" → Arsenal
* "mancity" → Man City
* "liverpol" → Liverpool

### 4. Context-Aware Responses

If information is missing, the CLI asks follow-up questions instead of failing.

Example:
<img width="1795" height="809" alt="image" src="https://github.com/user-attachments/assets/357725ff-c429-4ffa-9523-2a249fbd0dca" />

<img width="1792" height="918" alt="image" src="https://github.com/user-attachments/assets/24872981-ad6c-4642-a7e4-816fe6247590" />

<img width="1791" height="470" alt="image" src="https://github.com/user-attachments/assets/1dc128ea-fb55-4ae8-871f-99dd23f5c511" />

<img width="1800" height="789" alt="image" src="https://github.com/user-attachments/assets/29a9b3f8-f8a0-4b35-abd4-3dbf114ab365" />







## Supported Queries

### Standings

* show me the table
* current standings
* league table
* where is Arsenal

### Match Predictions

* predict arsenal vs liverpool
* who will win man city vs chelsea
* odds for tottenham vs newcastle

### Title Race

* title race
* who will win the league
* championship odds

### Team Analysis

* how's arsenal doing
* analyze liverpool
* info on chelsea

### What-If Scenarios

* what if arsenal beats liverpool
* what happens if man city loses

### Simulation

* run simulation
* simulate the season
* run monte carlo

---

## Why This Approach

Poisson models goal scoring as discrete, low-frequency events in a fixed window. This makes it a natural fit for football.

Monte Carlo simulation captures uncertainty by running thousands of possible seasons.

The result is not a single prediction, but a distribution of outcomes.

---

## Tech Stack

* Python
* pandas
* NumPy
* SciPy
* SQLite
* Rich
* fuzzywuzzy
* Flask

---

## Key Takeaways

* Probability becomes intuitive when applied
* Small changes in expected goals shift outcomes significantly
* Reliable simulations require scale
* Data accuracy matters when working with pandas
* Model design involves tradeoffs, not just math

---

## Future Improvements

* Dynamic team strength updates
* Goal difference as a tiebreaker
* Data-driven home advantage
* xG integration
* Historical backtesting
* Expanded CLI capabilities

---

## Getting Started

### Prerequisites

* Python 3.10+
* SQLite database `prem_data.db` in the project root

### Installation

```bash
git clone <repo-url>
cd PremierLeaguePredictor
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate         # macOS/Linux
pip install -r data/requirements.txt
```

### Run the CLI

```bash
cd services
python pl_predictor_cli.py
```

---

## Acknowledgments

* The Premier League
* SciPy documentation
* Rich library
