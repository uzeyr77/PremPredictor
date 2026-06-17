# Dashboard Deploy Guide

High-level breakdown of everything needed to ship the dashboard page (`GET /`). **Backend payload is now complete** — your focus is Jinja wiring and deploy config.

---

## Backend status: complete for v1

The dashboard API now returns **every section** in `index.html`. Routes already call `get_dashboard_summary()` — no new endpoints needed.

---

## How the backend fits together

```text
GET /  or  GET /api/dashboard
        │
        ▼
PredictionService.get_dashboard_summary()
        │
        ├── simulate_season()          ──► title_favorites, top_4_race, probs for table
        ├── get_project_final_points() ──► projected points
        ├── get_featured_fixture_pool()──► one fixture window + probs (reused everywhere)
        │
        ├── pick_big_match()           ──► featured_matches.big_match
        ├── pick_derby_from_pool()     ──► featured_matches.derby
        ├── analyze_pool_swings()      ──► featured_matches.critical_match + critical_games
        ├── build_hero_match()         ──► hero_match (MOTW section)
        ├── build_rich_projected_table() ──► projected_table (Now / Proj / Title / Top4 / Drop)
        ├── annotate_upcoming_fixtures() ──► upcoming_fixtures (sidebar cards + pick)
        ├── get_form_pulse()           ──► form_pulse (in-form / cold teams)
        └── repository.get_matchweek() ──► meta.matchweek
```

**Key idea:** `get_featured_fixture_pool()` runs once. Sidebar fixtures, featured pickers, and swing analysis all share the same candidate list — no duplicate `predict_match` loops for those sections.

**Performance note:** Swing/stakes use `SWING_SIMULATIONS_CAP = 500` (not full 10k) to keep deploy-day loads reasonable. Full Monte Carlo still runs once for headline probabilities.

---

## Full payload reference (for Jinja)

| Template section | Payload key | Shape |
|------------------|-------------|-------|
| Sidebar snapshot | `last_updated`, `simulation_count`, `meta.matchweek` | strings / int |
| Hero / MOTW | `hero_match` | fixture + probs + `badge`, `stakes`, `head_to_head`, `home_form`, `away_form` — or `null` |
| Critical games grid | `critical_games` | list of cards with `race`, `swing`, teams, probs |
| Featured (if split UI) | `featured_matches` | `{ big_match, derby, critical_match }` each nullable |
| Projected table | `projected_table` | rows with `current_points`, `projected_points`, `title_probability`, etc. |
| Right sidebar fixtures | `upcoming_fixtures` | list with `pick`, probs, teams |
| Form pulse | `form_pulse.in_form`, `form_pulse.cold` | `{ team, form: [W,D,L,...], ppg }` |
| Title / top-4 snippets | `title_favorites`, `top_4_race` | probability rows |

Probabilities are **0–1 floats**. In Jinja: `{{ (row.title_probability * 100)|round(1) }}%`

---

## predictions.py functions (engine layer)

| Function | Purpose |
|----------|---------|
| `simulate_season()` | Monte Carlo — title/top4/relegation probabilities |
| `get_project_final_points()` | Projected final points per team |
| `get_featured_fixture_pool()` | Upcoming matchweek window + W/D/L probs |
| `pick_big_match()` | Top-6 vs top-6 clash |
| `pick_derby_from_pool()` | First derby in pool |
| `find_derby_in_fixtures()` | Single-pair derby lookup |
| `analyze_pool_swings()` | Critical match + 3 race cards (one pass) |
| `score_fixture_swing_by_metric()` | Expected swing per title/top4/relegation |
| `build_hero_match()` | Hero card with H2H, form, stakes |
| `get_match_stakes()` | “What’s at stake” rows for hero |
| `get_head_to_head()` | Last 5 meetings (W/D/L from one team’s view) |
| `get_recent_form()` | Last N results per team from played matches |
| `get_team_form_snapshot()` | One team’s form + PPG |
| `get_form_pulse()` | Best/worst form teams |
| `build_rich_projected_table()` | Top 5 + separator + bottom 3 with all columns |
| `annotate_upcoming_fixtures()` | Adds `pick` label for sidebar |

## prediction_service.py

| Method | Purpose |
|--------|---------|
| `get_dashboard_summary()` | **Only method the dashboard route calls** — composes everything above |

## repository.py

| Method | Purpose |
|--------|---------|
| `get_matchweek()` | Current matchweek for sidebar “MD X” |
| `get_current_table()` | Raw standings for big-match filter + table “Now” column |
| `get_match_data()` | Used by form/H2H/historical helpers |

---

## Why these changes work together

1. **Pool first** — Define which upcoming games matter, then every picker reads the same list.
2. **One sim baseline** — `simulate_season` runs once; swing analysis reuses that baseline (no second full sim).
3. **Historical from DB** — Form and H2H read played rows from `match_data`; no new predictions needed.
4. **Hero = best story** — `build_hero_match` picks critical → big → derby, then enriches with form/H2H/stakes for the big MOTW block.
5. **Null-safe** — Derby, critical, hero can all be `null`; template must handle with `{% if hero_match %}`.

---

## Mental model: four layers

Think of the dashboard as four layers stacked bottom to top:

```text
┌─────────────────────────────────────┐
│  4. Frontend (index.html + Jinja)   │  ← YOUR FOCUS NOW
├─────────────────────────────────────┤
│  3. Routes (Flask)                  │  ← done
├─────────────────────────────────────┤
│  2. Service (PredictionService)     │  ← done
├─────────────────────────────────────┤
│  1. Engine + Repository             │  ← done
└─────────────────────────────────────┘
```

**Deploy rule:** smoke-test the API, then wire Jinja section by section.

---

## Your focus today: Jinja + routing polish

Routing exists. Do **not** add new dashboard routes. Work through:

### 1. Smoke test API (15 min)

```bash
set PLP_DB_PATH=services\prem_data.db
set PLP_DEFAULT_SIMULATIONS=500
python run.py
curl "http://127.0.0.1:5000/api/dashboard?simulations=500"
```

### 2. Wire `index.html` section by section

| Section | Jinja source |
|---------|--------------|
| Sidebar footer | `{{ last_updated }}`, `{{ simulation_count }}`, `{{ meta.matchweek }}` |
| Hero MOTW | `{% if hero_match %}...{{ hero_match.home_team }}...{% endif %}` |
| Critical games | `{% for game in critical_games %}` |
| Projected table | `{% for row in projected_table %}` — skip rows where `row.is_separator` |
| Sidebar fixtures | `{% for fx in upcoming_fixtures %}` — use `fx.pick` |
| Form pulse | `{% for team in form_pulse.in_form %}` |

### 3. Nav links (routing polish)

Replace `href="#"` with Flask `url_for`:

```jinja
<a href="{{ url_for('dashboard.dashboard_page') }}">Dashboard</a>
<a href="{{ url_for('predictions.predictions_page') }}">Predictions</a>
```

(Use actual blueprint endpoint names from your route files.)

### 4. Null checks

```jinja
{% if hero_match %}
{% if featured_matches.derby %}
{% if critical_games %}
```

### 5. Deploy config

- `PLP_DB_PATH` on server
- `PLP_DEFAULT_SIMULATIONS=500` until you add cache
- `FLASK_DEBUG=0` in production

---

## Phase 1 — Backend (complete)

All sections below are **implemented**. See payload reference above.

---

## Phase 2 — Performance (caching) — post-deploy or same day

### Why it matters

Every dashboard load currently runs:
1. Full `simulate_season` (Monte Carlo)
2. Multiple `predict_match` calls for fixture pool
3. Critical match: 3 scenario sims **per candidate fixture**

That can mean **10–30+ seconds** on first load in production (10k sims).

### Three-speed model

| Tier | Examples | Strategy |
|------|----------|----------|
| **Instant** | Current table, fixtures, derby labels | No sims; always fast |
| **Slow** | Title/top-4 probs, projected table | Cache 15–30 min |
| **Very slow** | Critical match swing | Cache separately; lower sim count |

### Minimum caching for deploy

You do not need Redis on day one. Pick one:

1. **In-memory TTL cache** on `get_dashboard_summary` (30 min) — biggest win, lowest effort
2. **Lower default sims** via `PLP_DEFAULT_SIMULATIONS=500` until cache exists
3. **Pre-warm script** (cron) that hits `/api/dashboard` after DB updates

**Invalidation:** include a DB fingerprint in the cache key (e.g. count of played matches + sum of points) so cache clears when results update.

See also: [`FEATURED_MATCHES_FIXES.md`](FEATURED_MATCHES_FIXES.md) deploy section.

---

## Phase 3 — Verify API (before touching HTML)

Routes are wired in [`routes/dashboard_routes.py`](../routes/dashboard_routes.py). Both endpoints use the same helper:

- `GET /` → HTML (will matter after Jinja)
- `GET /api/dashboard` → JSON (test this first)

### Local setup

```bash
set PLP_DB_PATH=services\prem_data.db
set PLP_DEFAULT_SIMULATIONS=500
python run.py
```

### Smoke test

```bash
curl "http://127.0.0.1:5000/api/dashboard?simulations=500"
```

### Confirm response includes

```json
{
  "last_updated": "...",
  "simulation_count": 500,
  "meta": { "matchweek": 38, "season": 2025, "season_label": "2025/26" },
  "title_favorites": [...],
  "top_4_race": [...],
  "projected_table": [...],
  "upcoming_fixtures": [...],
  "featured_matches": { "big_match": null, "derby": null, "critical_match": {...} },
  "critical_games": [...],
  "hero_match": {...},
  "form_pulse": { "in_form": [...], "cold": [...] }
}
```

### Tests to run

```bash
pytest tests/test_prediction_service.py::TestGetDashboardSummaryMocked -v
```

Optional later: route test with Flask test client (`client.get("/api/dashboard")`).

**Do not wire the template until this returns sane data.**

---

## Phase 4 — Frontend (Jinja) — **your main task**

[`templates/index.html`](../templates/index.html) is still static. The route passes the full payload via `render_template("index.html", **payload)`.

See **“Your focus today”** section above for the section-by-section map.

---

## Recommended order of work (updated)

```text
1. curl /api/dashboard — confirm JSON           (15 min)
2. Wire index.html section by section           (2–4 hrs)  ← deploy blocker
3. url_for nav links                            (30 min)
4. Null-safe featured/hero blocks               (30 min)
5. PLP_DB_PATH + lower sims on server           (15 min)
6. Deploy
7. TTL cache when you have time
```

---

## v1 deploy definition of done

- [ ] `GET /api/dashboard` returns all keys in `DashboardSummary`
- [ ] `GET /` renders live data in every major section
- [ ] Null slots hidden (no hero / derby / critical when absent)
- [ ] `PLP_DB_PATH` set on server
- [ ] Acceptable load time (`PLP_DEFAULT_SIMULATIONS=500` or cache)
- [ ] Contract test passes

Optional after launch: TTL cache, venue names on cards, full 20-row table page.

---

## Related docs

| Doc | Purpose |
|-----|---------|
| [`ROUTING_AND_FRONTEND_GUIDE.md`](ROUTING_AND_FRONTEND_GUIDE.md) | Route patterns, query params |
| [`SERVICE_LAYER_TESTING.md`](SERVICE_LAYER_TESTING.md) | Mocked vs integration tests |
| [`FEATURED_MATCHES_FIXES.md`](FEATURED_MATCHES_FIXES.md) | Featured match bugs fixed + lessons |
| [`models/contracts.py`](../models/contracts.py) | Exact payload shape for template |
