"""Stage F1 migration lifecycle tests."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def run_migration(database_url: str, revision: str, repo_root):
    environment = os.environ.copy()
    environment["AEROGUARD_DATABASE_URL"] = database_url
    alembic_config = str(repo_root / "backend" / "alembic.ini")
    return subprocess.run([sys.executable, "-m", "alembic", "-c", alembic_config, *revision.split()], cwd=repo_root, env=environment, capture_output=True, text=True, check=True)


def test_operational_migration_upgrade_downgrade_reupgrade(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    database_path = tmp_path / "operational.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    run_migration(database_url, "upgrade head", repo_root)
    connection = sqlite3.connect(database_path)
    tables = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
    expected_tables = {
        "sensors", "detections", "tracks", "track_history", "alerts",
        "threat_assessments", "scenarios", "geofences", "track_associations",
        "intelligence_snapshots", "track_group_history", "behavior_event_history",
        "incidents", "incident_events",
    }
    assert expected_tables.issubset(tables)
    run_migration(database_url, "downgrade 0004_audit_events", repo_root)
    tables_after_downgrade = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
    assert "sensors" not in tables_after_downgrade
    assert "intelligence_snapshots" not in tables_after_downgrade
    assert "incidents" not in tables_after_downgrade
    assert "incident_events" not in tables_after_downgrade
    run_migration(database_url, "upgrade head", repo_root)
    run_migration(database_url, "upgrade head", repo_root)
    connection.close()