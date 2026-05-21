"""
migrate_schema.py — Step 1 of 2: schema restructuring.

Merges results2015, results2019, results2021 into a single election_results
table (with a year column) and drops stale unused tables.

Run from the project root:
    .venv/Scripts/python.exe election_database/migrate_schema.py

A timestamped backup is written before any changes are made.
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

    # ── Create election_results ──────────────────────────────────────────────
    c.execute("DROP TABLE IF EXISTS election_results")
    c.execute("""
        CREATE TABLE election_results (
            id              INTEGER,
            year            INTEGER,
            party           TEXT,
            candidate       TEXT,
            votecount       INTEGER,
            votepercent     REAL,
            elected         INTEGER,
            incumbent       INTEGER,
            leanvsprovince  REAL,
            leanvsfederal   REAL
        )
    """)
    print("Created election_results")

    # ── Migrate 2015 + 2019 (source column: votepercentage) ─────────────────
    for src in ('results2015', 'results2019'):
        c.execute(f"""
            INSERT INTO election_results
            SELECT id, year, lower(party), candidate, votecount, votepercentage,
                   elected, incumbent, leanvsprovince, leanvsfederal
            FROM {src}
        """)
        print(f"Migrated {c.rowcount} rows from {src}")

    # ── Migrate 2021 (source column: votepercent) ────────────────────────────
    c.execute("""
        INSERT INTO election_results
        SELECT id, year, lower(party), candidate, votecount, votepercent,
               elected, incumbent, leanvsprovince, leanvsfederal
        FROM results2021
    """)
    print(f"Migrated {c.rowcount} rows from results2021")

    # ── Verify row counts before dropping sources ────────────────────────────
    rows_by_year = c.execute(
        "SELECT year, COUNT(*) FROM election_results GROUP BY year ORDER BY year"
    ).fetchall()
    print("\nRows in election_results by year:")
    for year, n in rows_by_year:
        print(f"  {year}: {n}")

    # ── Drop stale tables ────────────────────────────────────────────────────
    stale = ['results2015', 'results2019', 'results2021',
             'testtable', 'seatcountsims', 'ridingsims']
    for table in stale:
        c.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"Dropped {table}")

    conn.commit()
    conn.close()
    print("\nSchema migration complete.")


if __name__ == '__main__':
    main()
