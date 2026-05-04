"""
Central home for model constants and simulation defaults.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    home_advantage: float = 1.3
    league_average_goals: float = 1.4
    scoreline_cap: int = 20
    default_simulations: int = 10000


DEFAULT_SIMULATION_CONFIG = SimulationConfig()
