# Featured Matches — Fixes, Lessons, and Deploy Checklist

Fixes applied for issues **5, 7, 8, 9, 10, 11, 12** from the featured-match code review.

---

## Fixes applied

### 5 — `pick_big_match` position tie-break used wrong row order

**Problem:** Positions were assigned with `enumerate(current_table.iterrows())`, assuming row index = league rank. SQLite row order is not guaranteed.

**Fix:** Sort by `points` descending first, then assign positions 1..20.

```python
sorted_table = current_table.sort_values("points", ascending=False).reset_index(drop=True)
positions = {row["team"]: i + 1 for i, row in sorted_table.iterrows()}
```

**Lesson:** Never use DataFrame row index as business logic (rank, position) unless you sorted explicitly.

**Learn:** [pandas sort_values](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html)

---

### 7 — Derby lookup team names must match DB exactly

**Problem:** `DERBIES` keys must match `match_data.home_team` / `away_team` strings exactly. `"Manchester United"` ≠ `"Man United"`.

**Fix:** Verified names against DB (`Man City`, `Man United`, etc.). Added comment on `DERBIES` and expanded pairs using exact DB spellings.

**Verify yourself:**

```bash
python -c "import sqlite3; from config import load_config; c=sqlite3.connect(load_config().db_path); print(c.execute('SELECT DISTINCT home_team FROM match_data WHERE season=2025').fetchall())"
```

**Lesson:** Lookup tables keyed by strings are fragile — normalize names in one place or validate at startup.

**Learn:** [Python dict keys / hashable types](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict)

---

### 8 — `get_matchweek()` depended on row order

**Problem:** `played.tail(1)` returns the last **row**, not the highest matchweek.

**Fix:**

```python
return int(played["matchweek"].max())
```

**Lesson:** `.tail(1)` = positional last row. `.max()` = actual maximum value.

**Learn:** [pandas max](https://pandas.pydata.org/docs/reference/api/pandas.Series.max.html)

---

### 9 — Featured matches not wired into dashboard payload

**Problem:** `get_dashboard_summary()` still used `match_of_the_week: upcoming_fixtures[0]`.

**Fix:** Build `featured_matches` with three pickers and add to `DashboardSummary`:

```python
featured_matches = {
    "big_match": pick_big_match(pool, league_table),
    "derby": pick_derby_from_pool(pool),
    "critical_match": get_critical_upcoming_fixture(repo, pool, sims, simulations, seed),
}
```

**Lesson:** Engine helpers are useless until the service composes them into the API contract.

---

### 10 — Duplicate `simulate_season` on critical match path

**Problem:** `get_critical_upcoming_fixture` called `simulate_season` again even though the dashboard already ran it.

**Fix:** Pass `baseline` (and `pool`) into `get_critical_upcoming_fixture`. Dashboard reuses the same `sims` dict.

**Lesson:** Expensive work should run once per request and be passed down, not recomputed in every helper.

**Learn:** [DRY principle](https://en.wikipedia.org/wiki/Don%27t_repeat_yourself)

---

### 11 — Wrong return type on critical match

**Problem:** Annotated `list[dict] | None` but returned a single fixture dict.

**Fix:** Signature is now `-> dict | None`.

**Lesson:** Return types document intent — mismatch hides bugs in callers and tests.

**Learn:** [Python typing](https://docs.python.org/3/library/typing.html)

---

### 12 — No minimum swing threshold

**Problem:** Always returned a “critical” fixture even when swing ≈ 0.

**Fix:** `MIN_EXPECTED_SWING = 0.02` — if best score is below 2 percentage points, return `None`.

**Lesson:** Featured slots should be allowed to be empty; don’t force weak signal into the UI.

---

## Still open (not in this fix batch)

| Item | Status |
|------|--------|
| Critical match still slow (many scenario sims per fixture) | Cache or lower sim count for swing only |
| Duplicate `predict_all_remaining_matches` in dashboard path | Reuse pool/fixtures from one call |
| Derby pool scanner was missing | Fixed via `pick_derby_from_pool()` |

---

## What else is needed to deploy the dashboard

### Must-have (blocks deploy)

| Task | Why |
|------|-----|
| **Wire `index.html` to real data** | Template has zero Jinja variables — page is still static |
| **Set `PLP_DB_PATH`** | Point to real `prem_data.db` on server |
| **Verify `/api/dashboard` returns JSON** | Smoke test after wiring |
| **Handle empty featured slots in template** | `critical_match` / `derby` can be `null` |

### Should-have (same day)

| Task | Why |
|------|-----|
| **Lower sim count or cache dashboard** | First uncached load with critical match is very slow |
| **Update tests** for new `featured_matches` keys | Done for contract test; add route test optional |
| **Nav links** (`url_for`) | Currently `#` placeholders |

### Nice-to-have (post-launch)

| Task | Why |
|------|-----|
| Form pulse section | `get_recent_form` exists, not in payload |
| Rich projected table (title %, top 4 % per row) | Mockup columns not all in API |
| TTL cache + `cached_at` in sidebar | Performance / UX |
| Route-level integration tests | Only service tests today |

### Deploy smoke test

```bash
set PLP_DB_PATH=services\prem_data.db
set PLP_DEFAULT_SIMULATIONS=500
python run.py
curl http://127.0.0.1:5000/api/dashboard?simulations=500
```

Confirm response includes: `title_favorites`, `projected_table`, `upcoming_fixtures`, `featured_matches.big_match`, etc.

---

## Recommended learning resources (by mistake type)

| Mistake | Resource |
|---------|----------|
| pandas filtering / sorting | [10 minutes to pandas](https://pandas.pydata.org/docs/user_guide/10min.html) |
| `.tail()` vs `.max()` | [pandas indexing](https://pandas.pydata.org/docs/user_guide/indexing.html) |
| Service orchestration | Your `docs/SERVICE_LAYER_TESTING.md` |
| TypedDict contracts | [models/contracts.py](../models/contracts.py) |
| Mocking patch paths | [unittest.mock — where to patch](https://docs.python.org/3/library/unittest.mock.html#where-to-patch) |
| frozenset / dict keys | [Python sets / frozenset](https://docs.python.org/3/library/stdtypes.html#set-types-set-frozenset) |
