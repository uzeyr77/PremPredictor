from __future__ import annotations

import os
import threading
from datetime import datetime

import requests
from flask import Blueprint, current_app, jsonify, request

from database import get_db_connection

jobs_bp = Blueprint("jobs", __name__)


def _verify_job_secret() -> tuple[dict, int] | None:
    auth_header = request.headers.get('Authorization')
    expected = os.getenv('JOB_SECRET')

    if not expected:
        return {'error': 'JOB_SECRET not configured on server'}, 500

    if not auth_header or not auth_header.startswith('Bearer '):
        return {'error': 'Missing or invalid Authorization header'}, 401

    token = auth_header.removeprefix('Bearer ')
    if token != expected:
        return {'error': 'Invalid job secret'}, 403

    return None


TEAM_NAME_MAP = {
    'Brighton Hove': 'Brighton',
    'Coventry City': 'Coventry City',
    'Nottingham': 'Nottm Forest',
    'Leeds United': 'Leeds',
    'Liverpool': 'Liverpool',
    'Ipswich Town': 'Ipswich Town',
    'Chelsea': 'Chelsea',
    'Everton': 'Everton',
    'Tottenham': 'Tottenham',
    'Bournemouth': 'Bournemouth',
    'Aston Villa': 'Aston Villa',
    'Man City': 'Man City',
    'Sunderland': 'Sunderland',
    'Brentford': 'Brentford',
    'Newcastle': 'Newcastle',
    'Arsenal': 'Arsenal',
    'Fulham': 'Fulham',
    'Crystal Palace': 'Crystal Palace',
    'Hull City': 'Hull City',
    'Man United': 'Man United',
}


def _run_refresh_cache(app) -> None:
    with app.app_context():
        try:
            service = current_app.config["PREDICTION_SERVICE"]
            repo = current_app.config["PREDICTION_REPOSITORY"]
            cfg = current_app.config["APP_CONFIG"]

            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] refresh_cache job started", flush=True)

            fingerprint = repo.db_fingerprint()
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] db fingerprint: {fingerprint}", flush=True)

            payload = service.compute_dashboard_summary(cfg.default_simulations, cfg.default_seed)

            repo.upsert_cache('dashboard', fingerprint, payload)
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] dashboard cache updated OK", flush=True)

        except Exception as e:
            import traceback
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] FAILED: {type(e).__name__}: {e}", flush=True)
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Full traceback:", flush=True)
            traceback.print_exc()


@jobs_bp.post("/api/jobs/refresh-cache")
def trigger_refresh_cache():
    error = _verify_job_secret()
    if error:
        return error

    app = current_app._get_current_object()
    thread = threading.Thread(target=_run_refresh_cache, args=(app,), daemon=True)
    thread.start()

    return jsonify({
        'status': 'started',
        'job': 'refresh-cache',
        'message': 'Dashboard cache refresh running in background'
    }), 202


def _run_update_match_data(app) -> None:
    with app.app_context():
        try:
            cfg = current_app.config["APP_CONFIG"]
            season = cfg.current_season
            api_key = os.getenv("FOOTBALL_DATA_API_KEY")

            if not api_key:
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ERROR: FOOTBALL_DATA_API_KEY not set", flush=True)
                return

            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] update_match_data job started for season {season}", flush=True)

            url = f"https://api.football-data.org/v4/competitions/PL/matches?season={season}"
            response = requests.get(url=url, headers={'X-Auth-Token': api_key}, timeout=30)
            response.raise_for_status()
            matches = response.json().get('matches', [])
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] API returned {len(matches)} matches", flush=True)

            records = []
            skipped = []
            for match in matches:
                home = TEAM_NAME_MAP.get(match['homeTeam'].get('shortName'))
                away = TEAM_NAME_MAP.get(match['awayTeam'].get('shortName'))
                if home is None or away is None:
                    skipped.append((match['homeTeam'].get('shortName'), match['awayTeam'].get('shortName')))
                    continue

                finished = match.get('status') == 'FINISHED'
                score = match.get('score', {}).get('fullTime', {})
                records.append({
                    "season": str(season),
                    "matchweek": int(match["matchday"]),
                    "date": str(match["utcDate"]),
                    "home_team": home,
                    "away_team": away,
                    "home_goals": score.get('home') if finished else None,
                    "away_goals": score.get('away') if finished else None,
                    "played": 1 if finished else 0,
                })

            if skipped:
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] WARNING: {len(skipped)} matches skipped (unmapped teams)", flush=True)

            conn = get_db_connection()
            cursor = conn.cursor()
            updated_results = 0
            updated_dates = 0
            inserted = 0

            try:
                for r in records:
                    key = (r['season'], r['matchweek'], r['home_team'], r['away_team'])

                    if r['played'] == 1:
                        cursor.execute(
                            """
                            UPDATE match_data
                            SET home_goals = %s, away_goals = %s, played = 1, date = %s
                            WHERE season = %s AND matchweek = %s
                              AND home_team = %s AND away_team = %s
                              AND played = 0
                            """,
                            (r['home_goals'], r['away_goals'], r['date'], *key),
                        )
                        updated_results += cursor.rowcount
                        if cursor.rowcount > 0:
                            continue

                    cursor.execute(
                        """
                        UPDATE match_data
                        SET date = %s
                        WHERE season = %s AND matchweek = %s
                          AND home_team = %s AND away_team = %s
                          AND played = 0 AND date <> %s
                        """,
                        (r['date'], *key, r['date']),
                    )
                    updated_dates += cursor.rowcount

                    cursor.execute(
                        """
                        SELECT 1 FROM match_data
                        WHERE season = %s AND matchweek = %s
                          AND home_team = %s AND away_team = %s
                        """,
                        key,
                    )
                    if cursor.fetchone() is None:
                        cursor.execute(
                            """
                            INSERT INTO match_data
                                (season, matchweek, date, home_team, away_team, home_goals, away_goals, played)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                r['season'], r['matchweek'], r['date'],
                                r['home_team'], r['away_team'],
                                r['home_goals'] if r['home_goals'] is not None else 0,
                                r['away_goals'] if r['away_goals'] is not None else 0,
                                r['played'],
                            ),
                        )
                        inserted += 1

                conn.commit()
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] season {season}: {updated_results} results, "
                      f"{updated_dates} dates refreshed, {inserted} fixtures inserted", flush=True)

            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        except Exception as e:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] FAILED: {type(e).__name__}: {e}", flush=True)


@jobs_bp.post("/api/jobs/update-match-data")
def trigger_update_match_data():
    error = _verify_job_secret()
    if error:
        return error

    app = current_app._get_current_object()
    thread = threading.Thread(target=_run_update_match_data, args=(app,), daemon=True)
    thread.start()

    return jsonify({
        'status': 'started',
        'job': 'update-match-data',
        'message': 'Match data sync running in background'
    }), 202
