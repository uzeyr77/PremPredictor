import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.markdown import Markdown
from fuzzywuzzy import process, fuzz
import re
from datetime import datetime
import json

# Import your prediction functions
import sys
sys.path.insert(0, '.')
from predictions import (
    simulate_season,
    predict_match,
    predict_all_remaining_matches,
    simulate_scenario,
    compare_scenario,
    get_points_distribution,
    get_final_table,
    get_top_4_race,
    get_title_race,
    league_table
)

console = Console()

# ============================================================================
# INTENT RECOGNITION & NLU
# ============================================================================

class IntentRecognizer:
    """Recognizes user intent from natural language"""
    
    def __init__(self):
        # Get team names from database
        self.teams = league_table['team'].tolist()
        
        # Define intent patterns
        self.intents = {
            'standings': [
                'table', 'standings', 'league table', 'positions', 'rankings',
                'current standings', 'show me the table', 'where is', 'league position'
            ],
            'title_race': [
                'title', 'championship', 'who will win', 'title race', 'title odds',
                'who\'s going to win', 'winner', 'champions', 'title probabilities'
            ],
            'top_4': [
                'top 4', 'top four', 'champions league', 'cl spots', 'cl qualification',
                'top four race', 'champions league spots', 'ucl', 'top 4 odds'
            ],
            'relegation': [
                'relegation', 'bottom 3', 'bottom three', 'who\'s going down',
                'relegation battle', 'relegation zone', 'getting relegated'
            ],
            'predict_match': [
                'predict', 'vs', 'v ', ' v ', 'match', 'game', 'fixture',
                'who will win', 'odds for'
            ],
            'simulate': [
                'simulate', 'simulation', 'run simulation', 'monte carlo',
                'probabilities', 'chances', 'odds'
            ],
            'team_analysis': [
                'how is', 'how\'s', 'tell me about', 'analyze', 'analysis',
                'stats for', 'info on', 'information about'
            ],
            'scenario': [
                'what if', 'scenario', 'if', 'suppose', 'what would happen'
            ],
            'fixtures': [
                'fixtures', 'remaining matches', 'upcoming', 'next matches',
                'schedule', 'remaining games'
            ],
            'help': [
                'help', 'what can you do', 'commands', 'how to use',
                'guide', '?', 'options'
            ]
        }
    
    def recognize(self, user_input):
        """
        Recognize intent from user input
        
        Returns:
            tuple: (intent, confidence, entities)
        """
        user_input_lower = user_input.lower().strip()
        
        # Check for exact matches first
        for intent, patterns in self.intents.items():
            for pattern in patterns:
                if pattern in user_input_lower:
                    return intent, 1.0, self._extract_entities(user_input, intent)
        
        # Fuzzy match if no exact match
        all_patterns = []
        pattern_to_intent = {}
        for intent, patterns in self.intents.items():
            for pattern in patterns:
                all_patterns.append(pattern)
                pattern_to_intent[pattern] = intent
        
        match, score = process.extractOne(user_input_lower, all_patterns, scorer=fuzz.partial_ratio)
        
        if score > 60:  # Confidence threshold
            intent = pattern_to_intent[match]
            return intent, score/100, self._extract_entities(user_input, intent)
        
        return 'unknown', 0, {}
    
    def _extract_entities(self, user_input, intent):
        """Extract entities like team names from input"""
        entities = {}
        
        # Extract team names using fuzzy matching
        teams_found = []
        for team in self.teams:
            # Check if team name or part of it is in input
            if team.lower() in user_input.lower():
                teams_found.append(team)
            else:
                # Fuzzy match for typos
                match, score = process.extractOne(
                    team, 
                    user_input.split(),
                    scorer=fuzz.ratio
                )
                if score > 80:
                    teams_found.append(team)
        
        if teams_found:
            entities['teams'] = teams_found
        
        # Extract numbers for simulation runs
        numbers = re.findall(r'\d+', user_input)
        if numbers and intent == 'simulate':
            entities['n_simulations'] = int(numbers[0])
        
        return entities

recognizer = IntentRecognizer()

# ============================================================================
# DISPLAY FUNCTIONS (From previous version but enhanced)
# ============================================================================

def display_standings(df=None, highlight_team=None):
    """Display league standings with optional team highlighting"""
    if df is None:
        df = league_table.copy()
    else:
        df = df.copy()
    
    # Sort by points (descending), then goal difference, then goals for
    df = df.sort_values(
        by=['points', 'goal_difference', 'goals_for'], 
        ascending=[False, False, False]
    ).reset_index(drop=True)
    
    table = Table(
        title="⚽ Premier League Standings",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Pos", style="cyan", justify="center", width=4)
    table.add_column("Team", style="white", width=20)
    table.add_column("P", justify="center", width=3)
    table.add_column("W", justify="center", width=3)
    table.add_column("D", justify="center", width=3)
    table.add_column("L", justify="center", width=3)
    table.add_column("GD", justify="center", width=5)
    table.add_column("Pts", justify="center", width=4, style="bold green")
    
    for idx, row in df.iterrows():
        position = idx + 1  # Calculate position from sorted index
        
        # Highlight specific team if requested
        if highlight_team and row['team'] == highlight_team:
            style = "bold yellow"
        elif position <= 4:
            style = "bold blue"
        elif position >= 18:
            style = "bold red"
        else:
            style = "white"
        
        table.add_row(
            str(position),
            row['team'],
            str(row['played']),
            str(row['wins']),
            str(row['draws']),
            str(row['losses']),
            f"{row['goal_difference']:+d}",
            str(row['points']),
            style=style
        )
    
    console.print(table)

def display_probabilities(probs_dict, title="Probabilities", top_n=10, show_zeros=False):
    """Display probabilities with visual bars"""
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Rank", style="cyan", justify="center", width=5)
    table.add_column("Team", style="white", width=20)
    table.add_column("Probability", justify="right", width=15)
    table.add_column("Visualization", width=30)
    
    # Sort and filter
    sorted_probs = sorted(probs_dict.items(), key=lambda x: x[1], reverse=True)
    if not show_zeros:
        sorted_probs = [(t, p) for t, p in sorted_probs if p > 0]
    sorted_probs = sorted_probs[:top_n]
    
    for idx, (team, prob) in enumerate(sorted_probs, 1):
        # Create visual bar
        bar_length = int(prob * 30)
        bar = "█" * bar_length
        
        # Color based on probability
        if prob > 0.7:
            prob_style = "bold green"
        elif prob > 0.3:
            prob_style = "yellow"
        else:
            prob_style = "white"
        
        table.add_row(
            str(idx),
            team,
            f"{prob:.1%}",
            f"[{prob_style}]{bar}[/{prob_style}]"
        )
    
    console.print(table)

def display_match_prediction(home, away, prediction):
    """Display match prediction in a nice panel"""
    
    # Determine favorite
    probs = {
        'Home Win': prediction['home_win_prob'],
        'Draw': prediction['draw_prob'],
        'Away Win': prediction['away_win_prob']
    }
    favorite = max(probs, key=probs.get)
    
    content = f"""
[bold cyan]{home}[/bold cyan] vs [bold cyan]{away}[/bold cyan]

📊 Expected Score: [bold]{prediction['expected_home_goals']:.1f} - {prediction['expected_away_goals']:.1f}[/bold]

Probabilities:
  🏠 Home Win:  [green]{prediction['home_win_prob']:.1%}[/green]  {'█' * int(prediction['home_win_prob'] * 30)}
  🤝 Draw:      [yellow]{prediction['draw_prob']:.1%}[/yellow]  {'█' * int(prediction['draw_prob'] * 30)}
  ✈️  Away Win:  [red]{prediction['away_win_prob']:.1%}[/red]  {'█' * int(prediction['away_win_prob'] * 30)}

💡 Prediction: [bold]{favorite}[/bold] ([green]{probs[favorite]:.0%}[/green] confidence)
"""
    
    panel = Panel(
        content,
        title="⚽ Match Prediction",
        border_style="blue",
        box=box.DOUBLE
    )
    
    console.print(panel)

def display_team_analysis(team):
    """Display detailed team analysis"""
    
    # Get team's current stats
    team_row = league_table[league_table['team'] == team].iloc[0]
    
    # Calculate position by sorting
    sorted_table = league_table.sort_values(
        by=['points', 'goal_difference', 'goals_for'],
        ascending=[False, False, False]
    ).reset_index(drop=True)
    position = sorted_table[sorted_table['team'] == team].index[0] + 1
    
    # Run quick simulation
    console.print(f"\n[cyan]Running analysis for {team}...[/cyan]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Simulating season...", total=None)
        results = simulate_season(5000)
        dist = get_points_distribution(team, results)
    
    content = f"""
[bold cyan]Current Form:[/bold cyan]
  Position: [bold]{position}[/bold]
  Points: [bold]{team_row['points']}[/bold] from {team_row['played']} games
  Form: {team_row['wins']}W {team_row['draws']}D {team_row['losses']}L
  Goal Difference: [bold]{team_row['goal_difference']:+d}[/bold]

[bold cyan]Season Projection:[/bold cyan]
  Expected Final Points: [bold]{dist['median']:.0f}[/bold] points
  Best Case (95th): [green]{dist['p95']:.0f}[/green] points
  Worst Case (5th): [red]{dist['p5']:.0f}[/red] points
  Range: {dist['min']}-{dist['max']} points

[bold cyan]Probabilities:[/bold cyan]
  Title: [{'green' if results['title_probabilities'][team] > 0.5 else 'yellow'}]{results['title_probabilities'][team]:.1%}[/]
  Top 4: [{'green' if results['top_4_probabilities'][team] > 0.5 else 'yellow'}]{results['top_4_probabilities'][team]:.1%}[/]
  Relegation: [{'red' if results['relegation_probabilities'][team] > 0.1 else 'green'}]{results['relegation_probabilities'][team]:.1%}[/]
"""
    
    panel = Panel(
        content,
        title=f"📊 {team} Analysis",
        border_style="cyan",
        box=box.DOUBLE
    )
    
    console.print(panel)

# ============================================================================
# INTENT HANDLERS
# ============================================================================

def handle_standings(entities):
    """Handle standings request"""
    console.print()
    
    if 'teams' in entities and len(entities['teams']) > 0:
        # Highlight specific team
        team = entities['teams'][0]
        console.print(f"[cyan]Showing standings (highlighting {team}):[/cyan]\n")
        display_standings(highlight_team=team)
    else:
        display_standings()

def handle_title_race(entities):
    """Handle title race query"""
    console.print("\n[cyan]Calculating title race probabilities...[/cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Running 10,000 simulations...", total=None)
        results = simulate_season(10000)
    
    display_probabilities(
        results['title_probabilities'],
        title="🏆 Title Race Probabilities",
        top_n=10
    )

def handle_top_4(entities):
    """Handle top 4 query"""
    console.print("\n[cyan]Calculating Champions League qualification odds...[/cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Running 10,000 simulations...", total=None)
        results = simulate_season(10000)
    
    display_probabilities(
        results['top_4_probabilities'],
        title="🎯 Top 4 Probabilities",
        top_n=15
    )

def handle_relegation(entities):
    """Handle relegation query"""
    console.print("\n[cyan]Calculating relegation battle...[/cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Running 10,000 simulations...", total=None)
        results = simulate_season(10000)
    
    display_probabilities(
        results['relegation_probabilities'],
        title="⚠️ Relegation Probabilities",
        top_n=10
    )

def handle_predict_match(entities):
    """Handle match prediction"""
    teams = entities.get('teams', [])
    
    if len(teams) >= 2:
        home, away = teams[0], teams[1]
        console.print(f"\n[cyan]Predicting {home} vs {away}...[/cyan]\n")
        prediction = predict_match(home, away)
        display_match_prediction(home, away, prediction)
    else:
        # Interactive selection
        console.print("\n[yellow]I need two teams to predict a match.[/yellow]\n")
        
        all_teams = league_table['team'].tolist()
        
        home = Prompt.ask("Home team", choices=all_teams)
        away = Prompt.ask("Away team", choices=[t for t in all_teams if t != home])
        
        console.print()
        prediction = predict_match(home, away)
        display_match_prediction(home, away, prediction)

def handle_team_analysis(entities):
    """Handle team analysis request"""
    teams = entities.get('teams', [])
    
    if teams:
        team = teams[0]
        display_team_analysis(team)
    else:
        console.print("\n[yellow]Which team would you like to analyze?[/yellow]\n")
        all_teams = league_table['team'].tolist()
        team = Prompt.ask("Team", choices=all_teams)
        console.print()
        display_team_analysis(team)

def handle_simulate(entities):
    """Handle general simulation"""
    n_sims = entities.get('n_simulations', 10000)
    
    console.print(f"\n[cyan]Running {n_sims:,} season simulations...[/cyan]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("Simulating...", total=None)
        results = simulate_season(n_sims)
    
    console.print("[green]✓ Simulation complete![/green]\n")
    
    # Show all three
    display_probabilities(results['title_probabilities'], "🏆 Title Race", top_n=5)
    console.print()
    display_probabilities(results['top_4_probabilities'], "🎯 Top 4 Race", top_n=8)
    console.print()
    display_probabilities(results['relegation_probabilities'], "⚠️ Relegation Battle", top_n=5)

def handle_scenario(entities):
    """Handle what-if scenario"""
    console.print("\n[bold cyan]📝 Scenario Builder[/bold cyan]\n")
    console.print("Let's build a 'what-if' scenario!\n")
    
    overrides = []
    
    while True:
        console.print(f"[bold]Match #{len(overrides) + 1}[/bold] (or type 'done' to finish)")
        
        home = Prompt.ask("Home team (or 'done')")
        if home.lower() == 'done':
            break
        
        # Fuzzy match team name
        home_match, score = process.extractOne(home, league_table['team'].tolist())
        if score < 80:
            console.print(f"[red]Couldn't find team '{home}'. Try again.[/red]")
            continue
        home = home_match
        
        away = Prompt.ask("Away team")
        away_match, score = process.extractOne(away, league_table['team'].tolist())
        if score < 80:
            console.print(f"[red]Couldn't find team '{away}'. Try again.[/red]")
            continue
        away = away_match
        
        result = Prompt.ask(
            "Result",
            choices=['home_win', 'draw', 'away_win'],
            default='home_win'
        )
        
        overrides.append({'home': home, 'away': away, 'result': result})
        console.print(f"[green]✓ Added: {home} vs {away} → {result}[/green]\n")
    
    if not overrides:
        console.print("[yellow]No scenarios specified.[/yellow]")
        return
    
    # Show summary
    console.print("\n[bold]Scenario Summary:[/bold]")
    for o in overrides:
        console.print(f"  • {o['home']} vs {o['away']}: {o['result']}")
    
    if not Confirm.ask("\nRun simulation?"):
        return
    
    # Run simulations
    console.print("\n[cyan]Running baseline...[/cyan]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        task = progress.add_task("Simulating...", total=None)
        baseline = simulate_season(5000)
    
    console.print("[cyan]Running scenario...[/cyan]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, transient=True) as progress:
        task = progress.add_task("Simulating...", total=None)
        scenario = simulate_scenario(overrides, n_simulations=5000)
    
    # Compare
    console.print("\n[bold cyan]📊 Impact Analysis[/bold cyan]\n")
    comparison = compare_scenario(baseline, scenario, metric='title')
    
    # Show biggest movers
    comparison_sorted = comparison.sort_values('change', key=abs, ascending=False)
    
    table = Table(title="Title Race Changes", box=box.ROUNDED)
    table.add_column("Team", style="white")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Change", justify="right")
    
    for _, row in comparison_sorted.head(10).iterrows():
        if abs(row['change']) > 0.001:
            change_str = f"{row['change']:+.1%}"
            if row['change'] > 0:
                change_style = "bold green"
            elif row['change'] < 0:
                change_style = "bold red"
            else:
                change_style = "white"
            
            table.add_row(
                row['team'],
                f"{row['baseline_prob']:.1%}",
                f"{row['scenario_prob']:.1%}",
                f"[{change_style}]{change_str}[/{change_style}]"
            )
    
    console.print(table)

def handle_fixtures(entities):
    """Handle fixtures request"""
    console.print("\n[cyan]Loading remaining fixtures...[/cyan]\n")
    
    fixtures = predict_all_remaining_matches()
    
    table = Table(
        title="📅 Upcoming Fixtures",
        box=box.ROUNDED
    )
    
    table.add_column("Date", style="cyan")
    table.add_column("Home", width=15)
    table.add_column("Away", width=15)
    table.add_column("Prediction", justify="center")
    table.add_column("Confidence", justify="right")
    
    for _, match in fixtures.head(20).iterrows():
        probs = {
            'H': match['home_win_prob'],
            'D': match['draw_prob'],
            'A': match['away_win_prob']
        }
        pred = max(probs, key=probs.get)
        confidence = probs[pred]
        
        table.add_row(
            match['date'],
            match['home_team'],
            match['away_team'],
            pred,
            f"{confidence:.0%}"
        )
    
    console.print(table)
    console.print(f"\n[dim]Showing 20 of {len(fixtures)} remaining fixtures[/dim]")

def handle_help(entities):
    """Show help information"""
    help_text = """
# 🤖 Premier League Predictor - Help

## What can I do?

Just talk naturally! Here are some examples:

### View Standings
- "Show me the table"
- "Current standings"
- "Where is Arsenal?"

### Predictions
- "Predict Arsenal vs Liverpool"
- "Who will win Man City v Chelsea?"
- "Odds for Tottenham vs Newcastle"

### Probabilities
- "Title race odds"
- "Who will win the league?"
- "Top 4 chances"
- "Relegation battle"

### Team Analysis
- "How's Arsenal doing?"
- "Analyze Liverpool"
- "Tell me about Man City"

### Scenarios
- "What if Arsenal beats Liverpool?"
- "Run a scenario"
- "Create a what-if"

### Fixtures
- "Remaining matches"
- "Upcoming fixtures"
- "Schedule"

### General
- "Run simulation"
- "Simulate season"
- "Help"
- "Exit" or "Quit"

## Tips
- Team names are fuzzy matched (e.g., "ars" → "Arsenal")
- You don't need exact syntax
- Just describe what you want!
"""
    
    console.print(Markdown(help_text))

# ============================================================================
# MAIN INTERACTIVE LOOP
# ============================================================================

def main():
    """Main interactive loop"""
    
    # Welcome banner
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ⚽ PREMIER LEAGUE PREDICTOR - INTERACTIVE CLI ⚽        ║
║                                                              ║
║          Statistical Modeling & Monte Carlo Simulation       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    console.print(banner, style="bold cyan")
    console.print("\n[dim]Type your question naturally, or 'help' for examples, 'exit' to quit[/dim]\n")
    
    # Main loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            # Check for exit
            if user_input.lower() in ['exit', 'quit', 'q', 'bye']:
                console.print("\n[cyan]Thanks for using PL Predictor! ⚽[/cyan]\n")
                break
            
            # Recognize intent
            intent, confidence, entities = recognizer.recognize(user_input)
            
            # Debug (optional - remove in production)
            # console.print(f"[dim]Intent: {intent} (confidence: {confidence:.0%})[/dim]")
            
            # Route to handler
            if intent == 'standings':
                handle_standings(entities)
            elif intent == 'title_race':
                handle_title_race(entities)
            elif intent == 'top_4':
                handle_top_4(entities)
            elif intent == 'relegation':
                handle_relegation(entities)
            elif intent == 'predict_match':
                handle_predict_match(entities)
            elif intent == 'team_analysis':
                handle_team_analysis(entities)
            elif intent == 'simulate':
                handle_simulate(entities)
            elif intent == 'scenario':
                handle_scenario(entities)
            elif intent == 'fixtures':
                handle_fixtures(entities)
            elif intent == 'help':
                handle_help(entities)
            else:
                # Unknown intent - suggest help
                console.print(f"\n[yellow]Hmm, I'm not sure what you mean by '{user_input}'[/yellow]")
                console.print("[dim]Try 'help' to see what I can do![/dim]")
        
        except KeyboardInterrupt:
            console.print("\n\n[cyan]Goodbye! ⚽[/cyan]\n")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            console.print("[dim]Try rephrasing your question or type 'help'[/dim]")

if __name__ == '__main__':
    main()
