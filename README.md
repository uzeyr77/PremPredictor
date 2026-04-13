# Premier League Predictor

A statistical modeling tool that predicts Premier League outcomes using Poisson-based match simulations and Monte Carlo methods.

Built to apply probability, data analysis, and simulation to something real: football.

## Overview

The league table shows what has happened — this project focuses on what's likely to happen next.

Using two seasons of Premier League data stored in SQLite, the model:

- Estimates expected goals from team attack/defense strength
- Simulates thousands of matches and full seasons
- Outputs probabilities for titles, top-4 finishes, and relegation

It also supports match-level predictions and scenario analysis, all accessible through a conversational CLI.

## Key Features

**Match Prediction** — Poisson-based goal modeling producing win/draw/loss probabilities.

**Monte Carlo Simulation** — 10,000+ simulated seasons generating outcome distributions.

**Projected Table** — Blended PPG model (70% actual, 30% expected) extrapolated over remaining fixtures.

**Scenario Analysis** — Lock in specific results and re-simulate the season.

**Conversational CLI** — Ask questions naturally with fuzzy team name matching. No memorizing commands.

**Team Insights** — Current form, projected points, and probability breakdowns.

## How It Works

1. Match and team data is read from SQLite into pandas DataFrames
2. Expected goals are computed using attack/defense strength ratings
3. Poisson distribution models the probability of every possible scoreline
4. Remaining fixtures are resolved via weighted random sampling
5. Points are tallied across all 20 teams into a final table
6. Repeat thousands of times to build probability distributions

## The CLI

This isn't a traditional command-line tool with rigid syntax. It understands natural language:

```
You > Show me the table
You > Predict Arsenal vs Liverpool
You > Title race odds
You > How's Chelsea doing?
You > What if Man City beats Arsenal?
```

Team names are fuzzy matched — type "ars" and it resolves to "Arsenal." Typos are handled. If it needs more info, it asks.

## Why Poisson + Monte Carlo?

**Poisson** models goal scoring as discrete, low-frequency events in a fixed window — a natural fit for football.

**Monte Carlo** captures uncertainty across an entire season by simulating thousands of possible outcomes.

Instead of one predicted table, the model produces a distribution — a more honest view of what might happen.

## Tech Stack

- **Python** — core language
- **pandas** — data manipulation and table generation
- **NumPy** — weighted random sampling for simulations
- **SciPy** — Poisson PMF for match modeling
- **SQLite** — match data, team statistics, league tables
- **Rich** — styled terminal output, tables, progress spinners
- **fuzzywuzzy** — fuzzy string matching for team name recognition
- **Flask** — web dashboard

## Key Takeaways

- Probability becomes intuitive when applied to real systems
- Small changes in expected goals significantly shift match outcomes
- Reliable simulations require scale (10k+ runs)
- Data manipulation accuracy matters — pandas rewards precision
- Model design (like PPG blending) involves tradeoffs, not just math

## Future Improvements

- [ ] Dynamic team strength updates mid-season
- [ ] Goal difference as a tiebreaker in simulations
- [ ] Data-driven home advantage per team
- [ ] xG integration
- [ ] Historical backtesting
- [ ] Expanded CLI capabilities

## Acknowledgments

- The Premier League for providing endless drama to model
- SciPy documentation for making Poisson accessible
- Rich library for making terminal output worth looking at
