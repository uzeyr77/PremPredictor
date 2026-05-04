"""
Shared pytest fixtures.

Docs: https://docs.pytest.org/en/stable/reference/fixtures.html
"""

from __future__ import annotations

from pathlib import Path

import pytest


# Project root = .../PremierLeaguePredictor (parent of tests/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project_root() -> Path:
    """Absolute path to the repository root (where prem_data.db usually lives)."""
    return PROJECT_ROOT


@pytest.fixture
def prem_db_path(project_root: Path) -> str:
    """
    Path to SQLite used by integration tests.

    Skips if missing so CI without a DB copy does not fail.
    """
    db = project_root / "prem_data.db"
    if not db.is_file():
        pytest.skip(f"Integration test requires database at {db}")
    return str(db)


@pytest.fixture
def prediction_repository_memory():
    """In-memory repository — satisfies PredictionService constructor."""
    from services.repository import PredictionRepository

    return PredictionRepository(":memory:")


@pytest.fixture
def prediction_service(prediction_repository_memory):
    from services.prediction_service import PredictionService

    return PredictionService(repository=prediction_repository_memory)
