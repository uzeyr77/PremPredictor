# Dashboard Enhancement Opportunities

Three backend additions that would meaningfully improve the dashboard's information density. All are low-risk, additive changes.

---

## A. Attack / Defence Strength Columns (High Value)

**What:** Add `Att` and `Def` columns to the projected standings table.

**Why it's useful:** The current standings show probability outputs but not the *inputs* that drive them. Attack and defence strength (the Poisson λ parameters) give users an intuitive read on why a team projects where it does.

**Backend changes required:**

1. `services/repository.py` — add a new method:
   ```python
   def get_team_strengths(self) -> pd.DataFrame:
       with self._connect() as conn:
           return pd.read_sql_query(
               "SELECT team, attack_strength, defense_strength FROM prem_teams_2025",
               conn
           )
   ```

2. `services/prediction_service.py` — in `build_rich_projected_table()`, merge strength data onto each row so `attack_strength` and `defense_strength` are available as keys.

3. `models/contracts.py` — extend `ProjectedTableRow` with two optional fields:
   ```python
   attack_strength: float   # optional
   defense_strength: float  # optional
   ```

**Template display:** Color `Att > 1.1` green, `Att < 0.9` red. Invert logic for `Def` (lower = weaker defence). Format to 2 decimal places.

---

## B. W–D–L Record (Zero Backend Work)

**What:** Show wins, draws, losses per team in the standings.

**Why it's useful:** Current points alone don't tell you whether a team is 8W-0D-3L or 4W-8D-3L — very different trajectories.

**Backend changes required:**

The `league_table_2025` table already has `wins`, `draws`, `losses`. These columns are already fetched in `repository.get_current_table()`. They just need to be included in the dict that `build_rich_projected_table()` returns (currently they are dropped).

1. In `prediction_service.py`, ensure `wins`, `draws`, `losses` pass through to the projected table output dict.
2. Add optional fields to `ProjectedTableRow` in `models/contracts.py`.

**Template display:** Compact `8-0-3` string in a single narrow column, or as a tooltip on the team name cell.

---

## C. Form Trend Arrow (No Backend Change)

**What:** Show a directional arrow before the PPG value in the Form Pulse panel.

**Why it's useful:** A team with `ppg: 2.1` could be trending up (W on the last match) or crashing (L on the last match). The arrow surfaces this instantly.

**Template-only change** — derive from the existing `form[-1]` list already in the response:

```jinja
{% set last = team.form[-1] if team.form else '' %}
{% set arrow = '↑' if last == 'W' else ('↓' if last == 'L' else '→') %}
{% set arrow_cls = 'c-green' if last == 'W' else ('c-red' if last == 'L' else 'c-muted') %}
<span class="{{ arrow_cls }}" style="font-size:10px">{{ arrow }}</span>
```

Place this before the `.ppg` span in each `.form-row`.
