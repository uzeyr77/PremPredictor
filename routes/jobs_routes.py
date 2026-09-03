from __future__ import annotations

import os
import threading
from datetime import datetime
from flask import Blueprint, current_app, jsonify, request

from scripts.jobs.update_league_table import build_records_for_league_table, fetch_standings_for_league_table, sync_records_for_league_table
from scripts.jobs.refresh_cache import refresh_cache
from scripts.jobs.update_match_data import build_records_for_match_data, sync_match_data_records, fetch_matches 
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


def _run_refresh_cache(app) -> None:
    with app.app_context():
        try:
            repo = current_app.config["PREDICTION_REPOSITORY"]

            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] refresh_cache job started", flush=True)

            fingerprint = repo.db_fingerprint()
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] db fingerprint: {fingerprint}", flush=True)
            refresh_cache()
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
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] update_match_data job started", flush=True)
            matches = fetch_matches()
            records = build_records_for_match_data(matches)
            sync_match_data_records(records)
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] update_match_data complete", flush = True)
        except Exception as e:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] FAILED: {e}", flush = True)
    
            
            

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
    
    
def _run_update_league_table(app):
    with app.app_context():
        try:
             print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] update league table job started", flush = True)
             standings = fetch_standings_for_league_table()
             records = build_records_for_league_table(standings)
             sync_records_for_league_table(records)
             print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] update league table job complete", flush = True)
        except Exception as e:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] FAILED: {e}", flush = True)
            
@jobs_bp.post("/api/jobs/update-league-table")
def trigger_update_league_table():
    error = _verify_job_secret()
    
    if error:
        return error
    
    
    app = current_app._get_current_object()
    thread = threading.Thread(target=_run_update_league_table, args=(app,), daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'job': 'update-league-table',
        'message': 'league table sync running in background'
    }), 202

    return jsonify({
        'status': 'started',
        'job': 'refresh-cache',
        'message': 'cache refresh sync running in background'
    }), 202
    
    
    
