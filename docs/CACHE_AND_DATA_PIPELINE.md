# Cache, Match Sync & Simulation Pipeline — Full Walkthrough (A–Z)

This document explains **every recent change** related to:

1. Why dashboard loads were unusably slow  
2. How fixture reuse fixed that  
3. How stale-while-revalidate keeps users from waiting  
4. How `update_match_data` keeps Postgres fresh  
5. How `refresh_cache` writes the dashboard cache  
6. What is ready vs not ready for deploy  

Read this top-to-bottom. It is meant to be a study guide, not a changelog blurb.

---

## A. The problem we started with

### A1. What you wanted

A public dashboard where:

- Visitors open `/` and see predictions **immediately**
- Background jobs keep data fresh (match results + recomputed sims)
- Postgres is the source of truth (after migrating off SQLite)

### A2. What was going wrong

After the SQLite → Postgres migration:

1. **Task Scheduler / refresh jobs stopped successfully writing cache**  
   - Often due to working directory / `.env` not loading  
   - Or jobs crashed before `upsert_cache`

2. **Cache was stale since ~July 5**  
   - `dashboard_cache.computed_at` never moved

3. **When something *did* recompute, it took 12+ minutes and then crashed**  
   - Preseason `0 / 0` PPG → `NaN` → `int(NaN)` failure in projected table

4. **Even with only `sims=10`, work felt infinite**  
   - Because the expensive work was **not** “10 Monte Carlo loops”  
   - It was **re-predicting all ~380 fixtures over and over**

### A3. Key insight

There are **two different costs**:

| Cost | What it is | How often it should run |
|------|------------|-------------------------|
| **Poisson prediction** | For each fixture, compute home/draw/away probs (20×20 score grid) | **Once** per refresh |
| **Monte Carlo sampling** | Roll dice using those probs N times | N times, but cheap compared to Poisson |

The old dashboard path treated Poisson as free and ran it dozens of times.

---

## B. End-to-end architecture (after the changes)

```text
┌─────────────────────────────────────────────────────────────────┐
│  SCHEDULED JOBS (Windows Task Scheduler → .bat wrappers)        │
│                                                                 │
│  1) run_update_match_data.bat                                   │
│       → scripts/jobs/update_match_data.py                       │
│       → football-data.org API                                   │
│       → UPDATE/INSERT match_data in Postgres                    │
│                                                                 │
│  2) run_refresh_cache.bat                                       │
│       → scripts/jobs/refresh_cache.py                           │
│       → compute_dashboard_summary()  (FORCE recompute)          │
│       → UPSERT dashboard_cache                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  POSTGRES                                                       │
│  - match_data          (fixtures + results)                     │
│  - league_table_2026   (standings)                              │
│  - prem_teams_2026     (attack/defense strengths)               │
│  - dashboard_cache     (JSON payload for /)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  USER REQUEST  GET /  or  GET /api/dashboard                    │
│                                                                 │
│  PredictionService.get_dashboard_summary()                      │
│    → if dashboard_cache exists: return it IMMEDIATELY           │
│    → else (cold start only): compute once + write cache         │
│                                                                 │
│  routes/dashboard_routes.py                                     │
│    → HTML: render_template("index.html", **payload)             │
│    → JSON: jsonify(payload)                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Rule of thumb:** users read cache; jobs write cache.

---

## C. Why the sims felt so bad (before)

### C1. Dashboard compute path (old)

`compute_dashboard_summary()` roughly did:

1. `simulate_season()`  
   - internally called `predict_all_remaining_matches()` → **~380 Poisson predictions**
2. `get_featured_fixture_pool()`  
   - predicted featured matchweek fixtures again (small)
3. `analyze_pool_swings()` for each featured fixture (~10)  
   - for each of 3 outcomes (`home_win`, `draw`, `away_win`)  
   - called `simulate_scenario()`  
   - each scenario called `predict_all_remaining_matches()` **again** → **~380 Poisson each**
4. `build_hero_match()` / `get_match_stakes()`  
   - 3 more scenarios → **3 × ~380 Poisson again**

### C2. Rough math (preseason, 380 remaining fixtures)

Assume ~10 featured fixtures:

```text
Baseline predict:                 1 × 380 =   380
Swing scenarios:            10 × 3 × 380 = 11,400
Hero stakes scenarios:         3 × 380 = 1,140
────────────────────────────────────────────────
Total Poisson fixture passes ≈ 12,920 predictions
```

Each prediction evaluates a 20×20 score grid with SciPy `poisson.pmf` twice:

```text
≈ 12,920 × 400 × 2 ≈ 10 million SciPy calls
```

Monte Carlo with `n=10` is tiny next to that.

### C3. Why `sims=10` didn’t save you

`n_simulations` only controls:

```text
for sim in range(n_simulations):
    for match in remaining_fixtures:
        rng.choice(..., p=probs)
```

It does **not** stop `predict_all_remaining_matches()` from being called inside every scenario.

### C4. Observed runtime

| Attempt | Result |
|---------|--------|
| Old path | ~12 minutes, then crash on NaN |
| New path (reuse + NaN fix) | **~48 seconds**, cache written successfully |

---

## D. Fixture reuse (the big simplification)

### D1. Idea in one sentence

**Predict each remaining fixture once, then pass that dataframe into every consumer.**

### D2. What “predicted fixtures” looks like

`predict_all_remaining_matches(repo)` returns a DataFrame with columns like:

- `date`
- `home_team`
- `away_team`
- `home_win_prob`
- `draw_prob`
- `away_win_prob`
- `expected_home_goals`
- `expected_away_goals`

This is the **probability table** for the rest of the season.

### D3. Where reuse was wired

In `services/prediction_service.py` → `compute_dashboard_summary()`:

```text
predicted_fixtures = predict_all_remaining_matches(repo)   # ONCE

simulate_season(..., remaining_fixtures=predicted_fixtures)
get_featured_fixture_pool(..., predicted_fixtures=predicted_fixtures)
analyze_pool_swings(..., predicted_fixtures=predicted_fixtures)
build_hero_match(..., predicted_fixtures=predicted_fixtures)
```

### D4. Function signature changes (engine)

| Function | Change |
|----------|--------|
| `simulate_season(..., remaining_fixtures=None)` | Uses provided probs; else predicts |
| `simulate_scenario(..., predicted_fixtures=None)` | Filters out overridden match; reuses probs |
| `simulate_season_scenario(..., starting_points=None)` | Starts from overridden points table |
| `get_featured_fixture_pool(..., predicted_fixtures=None)` | Merges probs instead of re-predicting |
| `analyze_pool_swings` / `score_fixture_swing` / `get_match_stakes` / `build_hero_match` | Thread `predicted_fixtures` through |

### D5. How a scenario works now

Example: “What if Arsenal beat Coventry?”

```text
1. Take shared predicted_fixtures (380 rows with probs)
2. Add 3 points to Arsenal in a copy of the standings
3. Remove Arsenal vs Coventry from the fixture list
4. Monte Carlo the remaining 379 fixtures using existing probs
5. Compare title/top4/relegation probabilities to baseline
```

No second Poisson pass.

### D6. Bonus bug fixed along the way

Old `simulate_scenario` modified `current_points`, then called `simulate_season_scenario`, which **reloaded standings from the DB and ignored the overrides**.

Now `starting_points=current_points` is passed through, so scenario overrides actually affect the sim.

---

## E. Preseason NaN crash (why cache never wrote)

### E1. Root cause

With no games played:

```text
actual_ppg = points / played = 0 / 0 = NaN
```

That flowed into:

```text
blended_ppg → projected_final_points → int(NaN) → ValueError
```

Crash happened **after** ~12 minutes of sim work, **before** `upsert_cache`.

### E2. Fix

In `get_actual_ppg`:

- if `played == 0` → `actual_ppg = 0`

In `get_blended_ppg`:

- if `played == 0` → use **expected_ppg only**
- if `played > 0` → `0.7 * actual + 0.3 * expected`

Also merge by `team` so row alignment is safe.

Defensive guard in `build_rich_projected_table` for NaN projected points.

### E3. Why this matters for caching

Cache write is the last step. Any crash before it leaves users on old data forever.

---

## F. Stale-while-revalidate (SWR)

### F1. Your understanding (confirmed)

> Instead of cache miss → recompute for the user, serve stale data and recompute on the next schedule.

Yes. Exactly.

### F2. Old request path

```text
IF cache exists AND fingerprint matches AND not expired:
    serve cache
ELSE:
    compute now   ← user waits
    upsert cache
    serve
```

Problems:

- Expired cache (30 min) forced recompute on a visitor
- Fingerprint mismatch forced recompute on a visitor
- First visitor after a failed job waited forever

### F3. New request path (`get_dashboard_summary`)

```text
IF any dashboard_cache row exists:
    serve it immediately   ← even if “stale”
ELSE:
    cold start: compute + upsert + serve
```

### F4. Who refreshes then?

Only:

- `scripts/jobs/refresh_cache.py` (scheduled)
- Manual run of that script

`refresh_cache.py` **must not** call `get_dashboard_summary()` (that would early-return).  
It calls `compute_dashboard_summary()` directly, then `upsert_cache`.

### F5. What “stale” means in practice

| Situation | User sees | Background job |
|-----------|-----------|----------------|
| Cache 5 minutes old | Instant page | Optional refresh |
| Cache 3 hours old | Instant page (slightly old probs) | Should have refreshed; check Task Scheduler logs |
| No cache row at all | Slow first load once | Then everyone else is fast |

Tradeoff: users may briefly see odds computed before the latest match result until the next refresh job runs. That is intentional and correct for UX.

---

## G. `update_match_data` — full algorithm

File: `scripts/jobs/update_match_data.py`

### G1. Purpose

Keep Postgres `match_data` synced with football-data.org for the **current season** (`config.current_season`, default 2026).

### G2. Why rewrite was needed

Old script:

- Always `INSERT`ed every row
- Hardcoded `played=0` and goals `0`
- Could duplicate fixtures
- Not safe to schedule repeatedly

### G3. Bootstrap (Task Scheduler safe)

```text
1. Resolve project root = parents[2] of this file
2. Put project root on sys.path
3. load_dotenv(project_root / ".env")
4. Read season from load_config().current_season
```

### G4. Pipeline

```text
fetch_matches()
  GET /v4/competitions/PL/matches?season={SEASON}
  → list of API match objects

build_records(matches)
  map API shortName → DB team names via TEAM_NAME_MAP
  if status == FINISHED:
      played=1, real home/away goals
  else:
      played=0, goals=None
  skip unmapped teams (warn)

sync(records)
  for each record keyed by (season, matchweek, home, away):
      1) if finished and DB still played=0:
            UPDATE goals + played=1 + date
      2) else if unplayed and date changed:
            UPDATE date
      3) else if row missing:
            INSERT fixture
  commit (or rollback on error)
```

### G5. Idempotency

Running twice on the same day with no new results:

```text
0 results recorded, 0 kickoff dates refreshed, 0 fixtures inserted
```

That is success, not failure.

### G6. Wrapper

`scripts/jobs/run_update_match_data.bat`

- `cd` to project root
- append stdout/stderr to `logs/update_match_data.log`

---

## H. `refresh_cache` — full algorithm

File: `scripts/jobs/refresh_cache.py`

### H1. Purpose

Force a full dashboard recompute and store JSON in `dashboard_cache`.

### H2. Steps

```text
1. Bootstrap path + .env (same pattern as update_match_data)
2. load_config()
3. PredictionRepository().ensure_cache_schema()
4. fingerprint = db_fingerprint()
     = "{played_count}:{points_sum}" for current season
5. payload = compute_dashboard_summary(sims, seed)   # NEVER get_dashboard_summary
6. upsert_cache('dashboard', fingerprint, payload)
7. log elapsed time
```

### H3. Why force compute

If the job used `get_dashboard_summary()`, SWR would return the old cache and the job would never refresh.

### H4. Wrapper

`scripts/jobs/run_refresh_cache.bat` → `logs/refresh_cache.log`

### H5. Verified result (local)

```text
dashboard cache updated OK in 47.9s
Postgres computed_at: 2026-07-18T02:40:27Z
GET /api/dashboard → 200 in ~0.57s
```

---

## I. Recommended job order

Always run **match sync before cache refresh**:

```text
update_match_data
    ↓  (results/fingerprint may change)
refresh_cache
    ↓
dashboard_cache reflects new standings/fixtures
```

Suggested schedules:

| Job | Cadence |
|-----|---------|
| `run_update_match_data.bat` | Every 3–6 hours (more often on matchdays) |
| `run_refresh_cache.bat` | Every 30–60 minutes (or right after match sync) |

On matchdays, a chained approach is ideal:

```text
update_match_data → if exit 0 → refresh_cache
```

(You can do that with two Task Scheduler tasks with a short offset, or one bat that calls both.)

---

## J. Task Scheduler setup checklist

For each `.bat`:

| Field | Value |
|-------|--------|
| Action | Start a program |
| Program/script | Full path to `.bat` |
| Start in | `C:\Users\uzeyr\PremierLeaguePredictor` |
| Run whether user is logged on | Yes (if you want overnight runs) |

Also confirm:

- The scheduled user can read `.env`
- `python` is on that user’s PATH **or** edit the bat to use full `python.exe` path
- Logs appear under `logs\` after each run
- Exit code `0` in the log footer

---

## K. Config knobs that matter

From `config.py` / env:

| Variable | Meaning | Deploy tip |
|----------|---------|------------|
| `PLP_CURRENT_SEASON` | Season year in DB/API | `2026` |
| `PLP_CURRENT_SEASON_LABEL` | UI label | `2026/27` |
| `PLP_DEFAULT_SIMULATIONS` | Monte Carlo N for cache compute | start with `10`–`500` |
| `FLASK_ENV` / `FLASK_DEBUG` | prod vs dev | `production` / `0` |
| `DB_*` | Postgres connection | required |

`PLP_DB_PATH` is legacy SQLite and is **not** used by the live repository.

---

## L. Frontend payload transfer — is it ready?

### L1. Dashboard (`/` + `/api/dashboard`) — **YES, ready**

Flow:

```text
get_dashboard_summary()
  → dict (DashboardSummary)
  → dashboard_page: render_template("index.html", **payload)
  → dashboard_api: jsonify(payload)
```

`index.html` already consumes:

- `meta.season_label`, `meta.matchweek`
- `last_updated`, `simulation_count`
- `hero_match` (+ form, H2H, stakes, probs, xG)
- `title_favorites`, `top_4_race`
- `projected_table`
- `critical_games`
- `upcoming_fixtures`
- `form_pulse`

After a successful cache warm, opening `/` should render from Postgres cache in under a second.

### L2. Predictions page (`/predictions`) — **NOT ready yet**

Known bug in `routes/predictions_routes.py`:

```text
cfg.defualt_simulations  # typo
cfg.defualt_seed
```

You said this is fine to defer.

### L3. Fixtures page (`/fixtures`) — **NOT ready yet**

Service returns field `date`; template groups by `match_date` → Jinja `UndefinedError`.

Also deferred if dashboard-only is the v1 goal.

### L4. Deploy readiness summary

| Piece | Status |
|-------|--------|
| Postgres 2026 data | Ready |
| Team name alignment | Ready |
| Match sync script | Ready |
| Cache refresh script | Ready + verified (~48s) |
| SWR user path | Ready |
| Fixture reuse | Ready |
| Dashboard HTML/JSON | Ready |
| Predictions page | Blocked by typo |
| Fixtures page | Blocked by field mismatch |
| Task Scheduler tasks | Bat files ready; **you still create the tasks** |
| Public URL (Render/etc.) | Not done yet |

**For a dashboard-only shareable demo:** backend+cache+frontend dashboard path is ready once Task Scheduler (or manual refresh) keeps cache warm.

---

## M. How to verify everything yourself

### M1. Match sync

```powershell
cd C:\Users\uzeyr\PremierLeaguePredictor
python scripts\jobs\update_match_data.py
```

Expect something like:

```text
API returned 380 matches for season 2026
season 2026: N results recorded, ...
update_match_data complete
```

### M2. Cache warm

```powershell
python scripts\jobs\refresh_cache.py
```

Expect:

```text
dashboard cache updated OK in Xs
```

### M3. Postgres check

```sql
SELECT cache_key, fingerprint, computed_at, ttl_seconds
FROM dashboard_cache
WHERE cache_key = 'dashboard';
```

`computed_at` should be “just now”.

### M4. Fast user path

```powershell
python run.py
```

Open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/api/dashboard`

Second load should be fast; you should **not** see a flood of `Simulation 0/N` in the terminal for normal page hits.

### M5. Confirm SWR

1. Warm cache once  
2. Hit `/` (fast)  
3. Do **not** run refresh  
4. Wait > 30 minutes  
5. Hit `/` again → still fast (stale served)  
6. Run `refresh_cache.py` → `computed_at` updates  

---

## N. Mental model cheat sheet

```text
Poisson prediction  = expensive math about each match
Monte Carlo         = cheap dice rolls using those probs
Cache               = saved finished dashboard JSON
SWR                 = users always read cache; jobs rewrite cache
update_match_data   = truth about which games were played
refresh_cache       = truth about current probabilities
```

If users wait, something is computing on the request path.  
If odds are old, the refresh job isn’t running or is failing (check `logs\`).

---

## O. Files touched by these improvements

| File | Role |
|------|------|
| `services/predictions.py` | NaN fix, fixture reuse APIs, scenario starting points |
| `services/prediction_service.py` | SWR + predict-once in `compute_dashboard_summary` |
| `scripts/jobs/update_match_data.py` | Idempotent API → Postgres sync |
| `scripts/jobs/refresh_cache.py` | Forced recompute + upsert |
| `scripts/jobs/run_update_match_data.bat` | Scheduler wrapper + logging |
| `scripts/jobs/run_refresh_cache.bat` | Scheduler wrapper + logging |
| `config.py` | `current_season` / label (earlier season switch) |
| `services/repository.py` | 2026 tables + season filters (earlier season switch) |

---

## P. What to do next (practical order)

1. Create the two Task Scheduler tasks pointing at the `.bat` files  
2. Confirm logs update and `dashboard_cache.computed_at` moves  
3. Run `python run.py` and click through the dashboard  
4. When ready for a public URL: deploy to Render/Neon (separate from this pipeline)  
5. Later: fix predictions typo + fixtures `match_date` if you want those pages live  

---

*Document generated to match the codebase state after the cache/SWR/fixture-reuse work. If behavior drifts, treat the source files above as authority.*
