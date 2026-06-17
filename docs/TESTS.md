# Tests — Reading Guide

Plain-English walkthrough of every existing test in this project, the fixtures and config that hold them together, and the docs to read alongside each idea. This file is reference material, not a tutorial.

---

## 1. How pytest is wired up here

### 1.1 `pytest.ini`

```
[pytest]
pythonpath = .
testpaths = tests
markers =
    integration: uses real SQLite / large simulations (may be slow; optional in CI)
```

What each line does:

- `pythonpath = .` — adds the repo root to `sys.path`, so `from services.prediction_service import ...` resolves without a `src/` layout or installed package.
- `testpaths = tests` — pytest only collects from the `tests/` directory. Stops it from accidentally running stuff in `services/` or `scripts/`.
- `markers` — registers the custom `@pytest.mark.integration` decorator. Without this, pytest emits a `PytestUnknownMarkWarning` every time it sees one.

### 1.2 Test discovery rules

Pytest collects:

- Files named `test_*.py` or `*_test.py` inside `tests/`.
- Functions named `test_*`.
- Methods named `test_*` inside classes named `Test*` (the class must NOT define an `__init__`).

Helper functions like `_make_projected_points_df()` are ignored because of the leading underscore and missing `test_` prefix.

### 1.3 Run commands

```bash
# All tests except those marked integration:
pytest -m "not integration"

# Only the fast unit tests (same effect, more explicit):
pytest tests/test_prediction_service.py -m "not integration" -v

# Only integration (needs prem_data.db at project root):
pytest -m integration -v

# A single class or method:
pytest tests/test_prediction_service.py::TestRunScenarioMocked -v
pytest tests/test_prediction_service.py::TestPredictionServiceConstruction::test_service_accepts_prediction_repository -v
```

Flags worth knowing:

- `-v` verbose — shows each test name and result.
- `-x` stop at first failure.
- `-k "scenario"` substring filter on test names.
- `--lf` rerun only last-failed.
- `-s` don't capture stdout (lets `print()` reach the terminal — useful while debugging).

---

## 2. `tests/conftest.py` — shared fixtures

Conftest is auto-discovered by pytest. Anything you put here is available to every test file in the same directory tree as a fixture — no import needed.

| Fixture | Scope | Returns | Used for |
|---|---|---|---|
| `project_root` | function | `Path` to repo root | Locating files relative to the project. |
| `prem_db_path` | function | `str` path to `prem_data.db`, or **skips the test** if missing | Integration tests that need a real DB. The skip means CI won't fail just because someone doesn't have the SQLite file. |
| `prediction_repository_memory` | function | `PredictionRepository(":memory:")` | A repository pointing at an empty in-memory SQLite DB. Lets you construct the service without touching the file system. The DB itself is empty — queries against it would fail, so this fixture is only useful when the engine calls are mocked away. |
| `prediction_service` | function | `PredictionService(repository=...)` | The dependency-injected service object every mocked test uses as its subject under test. |

`function` scope means each test gets a fresh fixture instance — no state leaks between tests. That's the safe default; only widen the scope when fixture setup is expensive (e.g. spinning up a real DB).

Docs to read:

- Fixture basics: <https://docs.pytest.org/en/stable/explanation/fixtures.html>
- Fixture scopes: <https://docs.pytest.org/en/stable/how-to/fixtures.html#fixture-scopes>
- `pytest.skip` and friends: <https://docs.pytest.org/en/stable/how-to/skipping.html>

---

## 3. `tests/test_prediction_service.py` — what each test verifies

The file is divided into six classes. Classes here are purely organizational — pytest treats every `test_*` method inside a `Test*` class the same way it treats top-level test functions. There is no `setUp`/`tearDown`; everything that needs setup uses fixtures.

### 3.1 The patching rule used throughout

Every mocked test patches names where they are **used**, not where they are **defined**. So you'll see:

```python
@patch("services.prediction_service.simulate_season")
```

…not `services.predictions.simulate_season`. That's because `prediction_service.py` does `from services.predictions import simulate_season` at import time, which copies the reference into its own namespace. Patching the original wouldn't change the copy the service already grabbed.

This is the single most common source of confusion when learning `unittest.mock.patch`. If you remember nothing else from this section, remember that rule.

Docs:

- "Where to patch": <https://docs.python.org/3/library/unittest.mock.html#where-to-patch>
- `patch` as decorator: <https://docs.python.org/3/library/unittest.mock.html#patch>

### 3.2 Class-by-class breakdown

#### `TestPredictionServiceConstruction`

> **One method**: `test_service_accepts_prediction_repository`

What it asserts:

1. `PredictionService` can be built from a `PredictionRepository`.
2. The repository injected is the same one stored on `svc.repository` (identity check with `is`).
3. `svc.simulation_config` is populated by the dataclass default (`DEFAULT_SIMULATION_CONFIG`).

Why it matters: this is a constructor smoke test. If someone changes `PredictionService` to require an extra arg or stops storing the repository, this fails immediately and protects every other test in the file (which depends on the same wiring via `prediction_service` fixture).

No mocks. No DB. Pure object-graph check.

#### `TestGetDashboardSummaryMocked`

> **One method**: `test_dashboard_payload_matches_dashboard_summary_contract`

What's mocked:

- `services.prediction_service.simulate_season` → fake Monte Carlo output via `_make_simulate_season_return()`.
- `services.prediction_service.get_project_final_points` → fake projected table via `_make_projected_points_df()`.

What it asserts about the returned `DashboardSummary` payload (see `models/contracts.py`):

| Assertion | Why it's there |
|---|---|
| `set(payload.keys()) == {...}` | The `TypedDict` contract is fixed. Routes and templates rely on these exact keys; an accidental rename is caught here. |
| `payload["simulation_count"] == 123` | The service must echo the **caller's** `simulations` argument, not invent its own. Catches a class of bugs where the count gets overridden internally. |
| `last_updated` is a non-trivial string | Confirms the timestamp branch ran — a bug that left it as `None` or empty would slip past `isinstance(..., str)` alone, hence the length check. |
| `title_favorites` ≤ 3 entries, each row has `{team, title_probability, top_4_probability}` | Top-3 slice contract. |
| `top_4_race` ≤ 4 entries | Top-4 slice contract. |
| `projected_table` row shape `{position, team, points}` with `int`/`str` types | Catches accidental numpy/pandas types leaking into the JSON path. Flask's `jsonify` rejects `numpy.int64` silently in some versions and noisily in others — better to assert ints up front. |
| `mock_simulate_season.assert_called_once_with(prediction_service.repository, 123, None)` | Locks in the calling convention: the repository is the first positional arg, then `simulations`, then `seed`. Refactors that change this order break here. |

What it does **not** test: the math inside `simulate_season`. That's the engine's job to test, not the service's.

#### `TestRunScenarioMocked`

> **One method**: `test_run_scenario_empty_overrides_payload_shape`

What's mocked:

- `services.prediction_service.pred.get_team_probabilities`
- `services.prediction_service.pred.simulate_scenario`
- `services.prediction_service.league_table` — patched as a `DataFrame({"team": teams})` via a `with patch(...)` context manager.

⚠ **Heads-up about the `league_table` patch**: this patch references a name (`services.prediction_service.league_table`) that **does not exist in the current `prediction_service.py`**. Look at lines 168–198 of that file — `run_scenario` reads `self.repository.get_current_table()`, not a module-level `league_table`. The patch silently does nothing now (it patches an attribute that the code never reads), but it also means `run_scenario` is hitting `self.repository.get_current_table()` on an empty `:memory:` DB — and the test only passes because the assertions all happen on mocked downstream output. If the empty-DB call were to start raising instead of returning an empty DataFrame, this test would fail for the wrong reason. **This is a stale test that needs updating** — track it as a follow-up.

What it asserts (when it runs):

| Assertion | Why |
|---|---|
| Top-level keys = `{meta, overrides, baseline, scenario, comparison}` | Public contract for the `/scenario` route. |
| `out["overrides"] == []` | Service echoes the input list back as part of the payload (used by the UI to display "what scenario produced this"). |
| `meta` echoes `simulation_count` and `seed` | Same echo-the-input principle as the dashboard test. |
| `baseline` and `scenario` each contain four buckets (`title`, `top2`, `top4`, `relegation`) keyed by team | Locks in the probability layout consumed by the comparison view. |
| `comparison` has the four metric buckets (`title`, `top_4`, `top_2`, `relegation`) | These bucket names differ from `baseline`/`scenario` (`top4` vs `top_4`); the test guards that inconsistency intentionally. |
| Each comparison row has at least `{team, baseline_prob, scenario_prob, change, change_pct}` | Schema for the comparison rows. |

#### `TestGetAccuracyTrackingMocked`

> **One method**: `test_accuracy_tracking_json_dumps_round_trip`

What's mocked: every backend call the method makes — `get_data_freshness_metadata`, `backtest_model`, `get_accuracy_trend`, `get_team_error_profile`. All return tiny safe dicts/lists.

What it asserts:

1. `json.dumps(payload)` succeeds.
2. The result is a string.
3. `"latest"` is a top-level key.

The whole point: Flask routes will eventually call `jsonify(payload)`, which fails if the payload contains anything `json` doesn't know how to serialize — `datetime`, `numpy.int64`, `numpy.float64`, `set`, `pandas.Timestamp`, etc. Round-tripping through `json.dumps` here catches that class of bug at the service layer instead of at the HTTP boundary.

This is a **smoke test**, not an exhaustive contract test. It deliberately doesn't check the metric values because those come from the engine.

#### `TestGetUpcomingFixturesMocked`

> **One method**: `test_fixture_list_entries_have_stable_keys`

What's mocked: `services.prediction_service.pred.get_remaining_matches` returns a one-row DataFrame.

What it asserts:

1. The output list has one row (mapping over the input DataFrame works).
2. Each row has the expected keys including the renamed `match_date` (the engine column is `date`, the service relabels it).

⚠ **There's a real bug visible here.** Look at `prediction_service.py` lines 151–157 — the actual implementation only returns `match_date`, `home_team`, `away_team`. The test asserts a much richer set including `home_win_prob`, `expected_home_goals`, etc. Run this test today and it will fail. Either the test is aspirational (you wanted the route to expose probabilities and never finished the service), or the service was simplified and the test wasn't updated. **Decide which is correct, then fix the other.**

#### `TestPredictionServiceIntegration`

> Marked `@pytest.mark.integration` — only runs with `pytest -m integration`.
>
> **One method**: `test_backtest_model_metrics_ranges_via_service_accuracy`

What it does: calls `prediction_service.get_accuracy_tracking(season="2024", at_gameweek=38, checkpoints=[38])` end-to-end against the **real** repository and the **real** engine — so SQLite is opened, the 2024 match data is queried, and a 1-iteration Monte Carlo runs (the `1` passed inside `backtest_model` keeps it fast).

What it asserts:

- `mae_points` is a finite number (not `inf`/`NaN`) and ≥ 0.
- `top4_hit_count`, if present, is between 0 and 4.

It deliberately doesn't check exact values because the engine is randomized. It checks **plausible ranges** — a "is the math obviously broken?" guard, not a "is the math correct?" guard.

Why this is gated behind a marker: it requires `prem_data.db` (≈ MB-scale binary file you don't want in git), and it runs the engine, which is the slowest path in the codebase.

---

## 4. `tests/test_simulation_seed.py` — placeholders only

The file declares two empty test functions:

```python
def test_determinism():
    """ ... """

def test_variation():
    """ ... """
```

Both have empty bodies. Pytest will report them as **passing** (a function with no assertions trivially passes), which is misleading. Treat these as TODOs:

- `test_determinism` — same engine call + same `seed` → byte-identical output (probability dicts equal, `points_distribution` lists equal).
- `test_variation` — same call + different seeds → at least one probability differs.

Until the bodies are filled in, these tests provide false confidence. Either implement them or mark them `@pytest.mark.skip(reason="not implemented")` so they show up as skipped instead of green.

---

## 5. What is **not** currently tested (for your "write tests next" step)

Compiled by reading every module in `services/`, `routes/`, `models/`, plus `db.py` and `app_factory.py`:

| Area | Module | Current coverage |
|---|---|---|
| Repository SQL queries | `services/repository.py` | None. No tests build a fixture DB and verify each `get_*` returns expected shape/columns. |
| Engine math | `services/predictions.py` | None. Functions like `predict_match`, `goal_difference_to_expected_ppg`, `get_blended_ppg`, `compare_scenario` have no direct unit tests. |
| Validators | `services/validators.py` | None. `validate_team_name`, `validate_probability_triplet`, `validate_fixture_override` are pure functions and trivial to test. |
| Config loader | `config.py` | None. Env-var parsing branches (`PLP_DEFAULT_SIMULATIONS`, dev vs prod default, `PLP_DEFAULT_SEED`) are untested. |
| Determinism / seeds | `services/predictions.py::simulate_season` | Stub only (see §4). |
| Flask routes | `routes/*.py` | None. No use of the Flask test client. |
| App factory | `app_factory.py` | None. `create_app()` could be smoke-tested by asserting the registered blueprints and `app.config` keys. |
| Query-param parsing | `routes/query_params.py` | None. |
| `db.py` request scoping | `db.py` | None. |

These are listed in roughly increasing setup cost: validators and `compare_scenario` are 5-minute tests; route tests need a Flask test client and possibly a temp DB.

---

## 6. Patterns specific to this codebase you should know before writing tests

### 6.1 Patch where used

Already explained in §3.1. Repeating because you'll forget it once.

### 6.2 In-memory SQLite + temp tables

For repository tests that need a real DB without committing one to git, use `:memory:` plus a fixture that creates the schema and seeds rows in `setUp`. Pattern:

```python
import sqlite3
import pytest
from services.repository import PredictionRepository

@pytest.fixture
def seeded_repo(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE league_table_2025 (team TEXT, played INT, points INT)")
    conn.execute("INSERT INTO league_table_2025 VALUES ('Alpha', 10, 25)")
    conn.commit()
    conn.close()
    return PredictionRepository(str(db_path))
```

`tmp_path` is a built-in pytest fixture that gives you a per-test temporary directory and cleans it up. Don't use `:memory:` directly with the current repository because each `_connect()` call opens a fresh connection — different connections see different in-memory DBs. A real file path solves that.

Docs:

- `tmp_path`: <https://docs.pytest.org/en/stable/how-to/tmp_path.html>
- SQLite `:memory:` caveats: <https://docs.python.org/3/library/sqlite3.html#sqlite3-uri-tricks>

### 6.3 Flask test client (for future route tests)

```python
from app_factory import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_dashboard_route_returns_200(client):
    res = client.get("/")
    assert res.status_code == 200
```

Docs:

- Flask testing: <https://flask.palletsprojects.com/en/stable/testing/>

---

## 7. External docs — pick from these as you go

**Pytest:**

- Tutorial intro: <https://docs.pytest.org/en/stable/getting-started.html>
- Fixtures (the most important pytest feature): <https://docs.pytest.org/en/stable/explanation/fixtures.html>
- Parametrize (run one test against many inputs): <https://docs.pytest.org/en/stable/how-to/parametrize.html>
- Markers: <https://docs.pytest.org/en/stable/how-to/mark.html>
- Tmp paths: <https://docs.pytest.org/en/stable/how-to/tmp_path.html>
- Capturing stdout: <https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html>

**Mocking:**

- Mock library: <https://docs.python.org/3/library/unittest.mock.html>
- "Where to patch" (read this before writing any patch): <https://docs.python.org/3/library/unittest.mock.html#where-to-patch>
- `patch` as decorator vs context manager: <https://docs.python.org/3/library/unittest.mock.html#patch>

**Flask:**

- Application factories: <https://flask.palletsprojects.com/en/stable/patterns/appfactories/>
- Testing with the test client: <https://flask.palletsprojects.com/en/stable/testing/>

**Pandas in tests:**

- `pandas.testing.assert_frame_equal`: <https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_frame_equal.html>
- `pandas.testing.assert_series_equal`: <https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_series_equal.html>

**SQLite:**

- `sqlite3` module: <https://docs.python.org/3/library/sqlite3.html>

**Testing philosophy (one short read each, picked because they're calibrated for backend code):**

- "Test Pyramid" — Martin Fowler: <https://martinfowler.com/articles/practical-test-pyramid.html>
- "Mocks Aren't Stubs" — Martin Fowler: <https://martinfowler.com/articles/mocksArentStubs.html>

---

## 8. Quick checklist before merging a new test

- [ ] Filename starts with `test_`, function starts with `test_`, class starts with `Test`.
- [ ] No state leaks between tests (use fixtures, not module globals).
- [ ] If you patched something, patched the *imported* name in the consumer module, not the original.
- [ ] If you added an integration-flavored test, marked it `@pytest.mark.integration`.
- [ ] Test name describes the behavior, not the implementation: `test_returns_empty_list_when_no_overrides` ≫ `test_run_scenario_branch_3`.
- [ ] One logical assertion per test where reasonable; if a test has 10 asserts, they're all reinforcing the same contract.
- [ ] Ran `pytest -m "not integration" -v` and it passes.
