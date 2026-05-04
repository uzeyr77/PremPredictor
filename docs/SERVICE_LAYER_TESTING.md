# Service layer testing — full spec

This document matches the test implementation in [`tests/test_prediction_service.py`](../tests/test_prediction_service.py), shared fixtures in [`tests/conftest.py`](../tests/conftest.py), and config in [`pytest.ini`](../pytest.ini) at the project root.

---

## 1. What you are testing

| Layer | Responsibility | In this project |
|--------|----------------|-----------------|
| **Repository** | Read/write SQLite, return `pandas` frames | [`PredictionRepository`](../services/repository.py) |
| **Service** | Call engine functions, shape responses for JSON/templates | [`PredictionService`](../services/prediction_service.py) |
| **Engine** | Monte Carlo, backtests, probabilities | [`services/predictions.py`](../services/predictions.py) |

**Service tests** assert **contracts**: keys, types, and basic sanity — not “Arsenal must win 34.2%.” Probabilities change every run unless you fix random seeds everywhere.

---

## 2. Pytest building blocks (syntax you need)

### 2.1 Test discovery

- Any function or **method** named `test_*` in files named `test_*.py` is collected.
- **Classes** are optional: they only group tests; they do **not** need to inherit from `unittest.TestCase` when using pytest.

```text
Docs: https://docs.pytest.org/en/stable/explanation/goodpractices.html#test-discovery
```

### 2.2 Assertions

- Use plain `assert condition` (pytest rewrites assertions for informative failures).

```text
Docs: https://docs.pytest.org/en/stable/how-to/assert.html
```

### 2.3 Fixtures (`@pytest.fixture`)

- A fixture is a function that **produces a value** (e.g. `PredictionService` instance) for tests.
- Reference the fixture by **parameter name** in the test: `def test_foo(prediction_service): ...`

```text
Docs: https://docs.pytest.org/en/stable/reference/fixtures.html
```

### 2.4 Markers (`@pytest.mark.integration`)

- Tag slow or environment-dependent tests; run subsets with `-m integration` or `-m "not integration"`.

```text
Docs: https://docs.pytest.org/en/stable/how-to/mark.html
```

### 2.5 Patching (`unittest.mock.patch`)

- Replace a **name in the module under test** while a test runs.
- **Patch where the symbol is looked up**: because `prediction_service.py` does `from services.predictions import simulate_season`, you patch:

  `services.prediction_service.simulate_season`

  not `services.predictions.simulate_season` (unless code uses the latter form).

```text
Docs: https://docs.python.org/3/library/unittest.mock.html#unittest.mock.patch
```

Decorator order: **bottom decorator runs first** (closest to the function). Our dashboard test patches `get_project_final_points` first parameter, `simulate_season` second — matching the decorator stack from bottom to top.

---

## 3. Files added / changed

| File | Purpose |
|------|---------|
| [`pytest.ini`](../pytest.ini) | Sets `pythonpath = .` so top-level packages (`services`, `models`, `routes`) import from repo root; defines `integration` marker. |
| [`tests/conftest.py`](../tests/conftest.py) | `project_root`, `prem_db_path` (skips if DB missing), `prediction_repository_memory`, `prediction_service`. |
| [`tests/test_prediction_service.py`](../tests/test_prediction_service.py) | All class-grouped tests (see section 4). |
| [`services/validators.py`](../services/validators.py) | Validation helpers; kept free of heavy engine imports. |

---

## 4. Test classes — spec (what each test proves)

### `TestPredictionServiceConstruction`

| Test | Spec |
|------|------|
| `test_service_accepts_prediction_repository` | `PredictionService(repository=...)` stores the repository on `svc.repository`. Confirms the constructor contract expected by app factories. |

---

### `TestGetDashboardSummaryMocked`

| Test | Spec |
|------|------|
| `test_dashboard_payload_matches_dashboard_summary_contract` | With `simulate_season` and `get_project_final_points` patched to deterministic returns: payload matches [`DashboardSummary`](../models/contracts.py) — keys `last_updated`, `simulation_count`, `title_favorites`, `top_4_race`, `projected_table`; nested list rows have the correct field names and Python types; `simulation_count` equals the argument passed to `get_dashboard_summary`. |

**Why mocks:** `get_dashboard_summary` does not use `self.repository` today; it calls global engine functions. Mocking avoids SQLite and random Monte Carlo.

---

### `TestRunScenarioMocked`

| Test | Spec |
|------|------|
| `test_run_scenario_empty_overrides_payload_shape` | With `get_team_probabilities` and `simulate_scenario` patched, and `league_table` patched to a three-team frame: `run_scenario([], ...)` returns top-level keys `meta`, `overrides`, `baseline`, `scenario`, `comparison`; baseline/scenario each have `title`, `top2`, `top4`, `relegation`; comparison buckets `title`, `top_4`, `top_2`, `relegation` are lists whose rows include `baseline_prob`, `scenario_prob`, `change`, `change_pct`. |

**Why patch `league_table`:** Scenario methods iterate `league_table["team"]`; the mock must list the same teams as the probability mocks.

---

### `TestGetAccuracyTrackingMocked`

| Test | Spec |
|------|------|
| `test_accuracy_tracking_json_dumps_round_trip` | With `backtest_model`, `get_accuracy_trend`, `get_team_error_profile`, `get_data_freshness_metadata` patched: `json.dumps(service.get_accuracy_tracking(...))` succeeds (no non-JSON types leaking). |

**Why:** Flask `jsonify` will fail on `datetime`, `numpy.float64`, raw sets, etc.

---

### `TestGetUpcomingFixturesMocked`

| Test | Spec |
|------|------|
| `test_fixture_list_entries_have_stable_keys` | With `pred.get_remaining_matches` returning one-row DataFrame: each entry has exactly `match_date`, `home_team`, `away_team`, `home_win_prob`, `away_win_prob`, `expected_home_goals`, `expected_away_goals`. |

---

### `TestPredictionServiceIntegration` (`@pytest.mark.integration`)

| Test | Spec |
|------|------|
| `test_backtest_model_metrics_ranges_via_service_accuracy` | **Only runs if** `prem_data.db` exists at project root (`conftest` skips otherwise). Calls real `get_accuracy_tracking` (no mocks): asserts `mae_points` is finite and non-negative; if `top4_hit_count` exists, in `[0, 4]`. |

**Why optional:** Imports `services.predictions`, which uses a **hardcoded DB path** and scientific stack; CI without your DB or without `scipy`/`sklearn` will skip or fail unless dependencies and DB are present.

---

## 5. How to run

From repository root (`PremierLeaguePredictor`):

```powershell
# Fast tests only (no integration marker)
python -m pytest tests/test_prediction_service.py -m "not integration" -v

# Integration tests only (needs prem_data.db + full stack)
python -m pytest tests/test_prediction_service.py -m integration -v

# Everything
python -m pytest tests/test_prediction_service.py -v
```

---

## 6. Dependencies required for collection / execution

Importing [`prediction_service.py`](../services/prediction_service.py) imports [`services/predictions.py`](../services/predictions.py), which requires **numpy**, **pandas**, **scipy**, **scikit-learn**, etc.

Install (example):

```powershell
pip install pandas numpy scipy scikit-learn flask pytest
```

If `ModuleNotFoundError` appears during **collection**, install the missing package or refactor the engine to lazy-import heavy libraries (out of scope for this doc).

---

## 7. Extending the suite (checklist)

1. **Add a method test** in a new or existing class; name it `test_*`.
2. Prefer **patching** engine calls on `services.prediction_service` for speed.
3. Assert **keys and types** first; add range checks (`math.isfinite`, bounds) for numeric metrics.
4. Use **`@pytest.mark.integration`** when the real DB or long simulations are unavoidable.
5. Add shared setup to [`tests/conftest.py`](../tests/conftest.py) as new `@pytest.fixture` functions.

---

## 8. Further reading (official)

| Topic | URL |
|--------|-----|
| Pytest getting started | https://docs.pytest.org/en/stable/getting-started.html |
| Fixtures reference | https://docs.pytest.org/en/stable/reference/fixtures.html |
| `unittest.mock` — where to patch | https://docs.python.org/3/library/unittest.mock.html#where-to-patch |
| TypedDict contracts | https://docs.python.org/3/library/typing.html#typing.TypedDict |

---

## 9. Why repository doubles are not used in these tests

`PredictionService` methods currently call **`services.predictions`** directly for simulations; **`self.repository` is rarely used**. A fake `PredictionRepository` would not change behavior until you **refactor** the service to load standings via `repository.get_current_table()`.

When you do that refactor, add fixtures that return deterministic DataFrames and assert the service passes them into the engine (or assert resulting payload fields).

---

_End of spec._
