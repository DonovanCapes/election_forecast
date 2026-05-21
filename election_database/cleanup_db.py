"""
cleanup_db.py - Step 3: table renames, column cleanup, ridings schema update.

1. Renames election_results  -> riding_results
2. Renames electionresults   -> federal_results
3. Drops the diff column from federal_results
4. Adds redistricting_year to ridings and sets current rows to 2022

Run from the project root:
    .venv/Scripts/python.exe election_database/cleanup_db.py

A timestamped backup is written before any changes are made.
Idempotent: each step checks whether it is needed before executing.
"""

import sqlite3
import shutil
from datetime import datetime

DB_PATH = 'election_database/election_database.db'


def backup(db_path):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = db_path.replace('.db', f'_backup_{ts}.db')
    shutil.copy2(db_path, dest)
    print(f"Backup written to {dest}")


def main():
    backup(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    existing_tables = {r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    # Rename election_results -> riding_results
    if 'election_results' in existing_tables:
        c.execute("ALTER TABLE election_results RENAME TO riding_results")
        print("Renamed election_results -> riding_results")
    else:
        print("Skip: election_results already renamed")

    # Rename electionresults -> federal_results
    if 'electionresults' in existing_tables:
        c.execute("ALTER TABLE electionresults RENAME TO federal_results")
        print("Renamed electionresults -> federal_results")
    else:
        print("Skip: electionresults already renamed")

    # Drop diff column from federal_results
    federal_cols = [r[1] for r in c.execute("PRAGMA table_info(federal_results)").fetchall()]
    if 'diff' in federal_cols:
        c.execute("ALTER TABLE federal_results DROP COLUMN diff")
        print("Dropped diff from federal_results")
    else:
        print("Skip: diff column already dropped")

    # Add redistricting_year to ridings
    ridings_cols = [r[1] for r in c.execute("PRAGMA table_info(ridings)").fetchall()]
    if 'redistricting_year' not in ridings_cols:
        c.execute("ALTER TABLE ridings ADD COLUMN redistricting_year INTEGER")
        c.execute("UPDATE ridings SET redistricting_year = 2022")
        print(f"Added redistricting_year to ridings, set {c.rowcount} rows to 2022")
    else:
        print("Skip: redistricting_year already exists")

    conn.commit()

    # Verify
    print("\nFinal table list:")
    tables = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    for (name,) in tables:
        n = c.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({name})").fetchall()]
        print(f"  {name} ({n} rows): {cols}")

    conn.close()
    print("\nCleanup complete.")


if __name__ == '__main__':
    main()
