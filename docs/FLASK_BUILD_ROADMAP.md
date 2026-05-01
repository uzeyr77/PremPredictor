# Premier League Predictor - Senior Engineer Build Roadmap

This roadmap is intentionally practical and implementation-first.
Think of it like constructing a stadium:

- **Phase 1** lays foundations (data and service contracts).
- **Phase 2** builds entrances and pathways (routes/API).
- **Phase 3** builds the fan experience (templates/frontend).

The goal is to help you build it yourself with confidence, not hide complexity.

---

## 0) Target Outcome

A robust Flask app with clear backend boundaries and at least these pages:

1. Main dashboard
2. Predictions in detail
3. Upcoming fixtures
4. Accuracy tracking (recommended as page 4)

Your current engine already has strong prediction logic. The main work now is architecture, contracts, reliability, and page wiring.

---

## 1) Delivery Sequence (What to build, in order)

## Phase 1 - Backend Hardening (Do this first)

### Why this phase matters
Right now, prediction logic and data access are tightly coupled. If you build UI first, you will keep reworking routes later.
This phase creates stable interfaces the UI can rely on.

### Files to create/complete
- `boilerplate/config.py`
- `boilerplate/services/simulation_config.py`
- `boilerplate/services/repository.py`
- `boilerplate/services/validators.py`
- `boilerplate/services/prediction_service.py`
- `boilerplate/models/contracts.py`

### Functions to implement
- Repository:
  - `get_current_table()`
  - `get_team_statistics()`
  - `get_match_data()`
  - `assert_required_tables()`
- Validators:
  - `validate_team_name()`
  - `validate_fixture_override()`
  - `validate_probability_triplet()`
- Service:
  - `get_dashboard_summary()`
  - `get_detailed_predictions()`
  - `get_upcoming_fixtures()`
  - `run_scenario()`
  - `get_accuracy_tracking()`

### Config and standards
- Use env var `PLP_DB_PATH` for database path (avoid hardcoded absolute paths).
- Add simulation defaults in one place (seed, number of sims, goal cap).
- Return structured payloads for every route (same shape every time).

### Exit criteria (Phase 1 done when)
- Service methods return valid structured dictionaries with no UI assumptions.
- Validation catches invalid teams/scenarios before simulation starts.
- Data readiness check exists and fails fast with clear errors.

---

## Phase 2 - API and Route Layer

### Why this phase matters
Routes should be thin orchestration only. They should call service methods and render/return payloads.
This keeps logic testable and reusable.

### Files to create/complete
- `boilerplate/app_factory.py`
- `boilerplate/routes/dashboard_routes.py`
- `boilerplate/routes/predictions_routes.py`
- `boilerplate/routes/fixtures_routes.py`
- `boilerplate/routes/accuracy_routes.py`
- `boilerplate/run.py`

### Routes to implement first
- Page routes:
  - `/` (dashboard)
  - `/predictions`
  - `/fixtures`
  - `/accuracy`
- API routes:
  - `/api/dashboard`
  - `/api/predictions`
  - `/api/fixtures`
  - `/api/scenario` (POST)
  - `/api/accuracy`

### Exit criteria (Phase 2 done when)
- Every page route can render with real data from `prediction_service`.
- Every API route returns JSON with predictable shape.
- Errors return proper status code + message.

---

## Phase 3 - Frontend Integration and Page UX

### Why this phase matters
Once backend contracts are stable, UI iteration becomes much faster.

### Files to create/complete
- `templates/base.html`
- `templates/index.html`
- `templates/predictions.html`
- `templates/fixtures.html` (new)
- `templates/accuracy.html`
- optional `static/css/app.css`
- optional `static/js/*.js`

### What to build on each page
- Dashboard:
  - Key cards (title favorite, top 4 certainty, sim count, last updated)
  - Current table and top-race snippets
- Predictions:
  - Full table projection
  - Title/top4/top2 probabilities
  - Scenario form and delta output
- Fixtures:
  - Remaining fixtures
  - Home/draw/away percentages
  - Expected goals and confidence tags
- Accuracy:
  - Last gameweek summary
  - Trend by gameweek
  - Error metrics glossary

### Exit criteria (Phase 3 done when)
- 3-4 pages all render from live contracts.
- User can run a scenario from UI.
- Accuracy page explains model quality clearly.

---

## 2) Architecture Rules (Non-negotiable)

1. **No prediction math in Flask routes**
2. **No direct SQL in templates or routes**
3. **No hardcoded local DB path in logic modules**
4. **Validate inputs before simulation**
5. **Keep response contracts explicit and typed**
6. **Add logging around expensive simulation calls**

---

## 3) Suggested Configs

- Environment variables:
  - `FLASK_ENV`
  - `FLASK_DEBUG`
  - `PLP_DB_PATH`
  - `PLP_DEFAULT_SIMULATIONS`
  - `PLP_DEFAULT_SEED` (optional)
- Dev dependencies:
  - `pytest`
  - `python-dotenv`

---

## 4) Testing Strategy (Minimum)

### Unit tests
- `predict_match` contract shape + probability sum
- `run_scenario` invalid fixture handling
- `get_upcoming_fixtures` output schema

### Integration tests
- `/api/dashboard` returns 200 + required keys
- `/api/scenario` handles bad payload with 400

### Regression checks
- fixed-seed simulation snapshot (to detect accidental math changes)

---

## 5) Immediate Build Plan for You (Next 5 coding sessions)

1. Implement repository + validators + service stubs.
2. Wire app factory + blueprints.
3. Build `/`, `/predictions`, `/fixtures` server-rendered pages.
4. Add scenario POST API and connect basic UI form.
5. Add accuracy ingestion + accuracy page.

---

## 6) Read This Before Coding

You already solved the hard analytics core. What remains is software engineering structure.
If you treat this as "design contracts first, implementation second", you will ship faster and with fewer rewrites.

