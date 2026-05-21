"""
import_2025_results.py — Step 2 of 2: import 2025 actual election results.

Cleans 2025_fed_election_results.csv and loads it into the election_results
table. Also adds a voteshare2025 column to electionresults.

Run from the project root AFTER migrate_schema.py:
    .venv/Scripts/python.exe election_database/import_2025_results.py

A timestamped backup is written before any changes are made.
"""

import re
import sqlite3
import shutil
import pandas as pd
from datetime import datetime

DB_PATH  = 'election_database/election_database.db'
CSV_2025 = 'election_database/2025_fed_election_results.csv'

# Order matters — check more specific patterns before shorter substrings.
# Liberal and Conservative are anchored to the slash separator so that fringe
# parties containing those words elsewhere in their name don't match.
PARTY_PATTERNS = [
    ('ndp', r'NDP'),
    ('gpc', r'Green Party'),
    ('bq',  r'Bloc'),
    ('ppc', r"People's Party"),
    ('lpc', r'\bLiberal/'),       # matches "Liberal/Libéral" only
    ('cpc', r'\bConservative/'),  # matches "Conservative/Conservateur" only
]

# Maps party codes to the labels used in electionresults
PARTY_LABEL_MAP = {
    'lpc': 'LPC', 'cpc': 'CPC', 'ndp': 'NDP',
    'gpc': 'GPC', 'bq':  'BQ',  'ppc': 'PPC',
}


def extract_party(s):
    for code, pattern in PARTY_PATTERNS:
        if re.search(pattern, s):
            return code
    return 'other'


def extract_name(s):
    """Return candidate name, stripping ** and the party suffix."""
    s_clean = s.replace('**', '').strip()
    for _, pattern in PARTY_PATTERNS:
        match = re.search(pattern, s_clean)
        if match:
            return s_clean[:match.start()].strip()
    return s_clean.split('/')[0].strip()


def backup(db_path):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = db_path.replace('.db', f'_backup_{ts}.db')
    shutil.copy2(db_path, dest)
    print(f"Backup written to {dest}")


def main():
    backup(DB_PATH)

    # ── Load and clean CSV ───────────────────────────────────────────────────
    df = pd.read_csv(CSV_2025, encoding='latin-1')
    df.columns = [
        'province', 'district_name', 'id', 'candidate_raw',
        'residence', 'occupation', 'votecount', 'votepercent',
        'majority', 'majority_pct',
    ]

    df['party']          = df['candidate_raw'].apply(extract_party)
    df['candidate']      = df['candidate_raw'].apply(extract_name)
    df['incumbent']      = df['candidate_raw'].apply(lambda x: 1 if '**' in x else 0)
    df['elected']        = df['majority'].apply(lambda x: 0 if pd.isna(x) else 1)
    df['year']           = 2025
    df['leanvsprovince'] = None
    df['leanvsfederal']  = None

    # ── Summary before committing ────────────────────────────────────────────
    print("Party extraction summary:")
    print(df['party'].value_counts().to_string())
    print(f"\nIncumbent candidates detected: {df['incumbent'].sum()}")
    print(f"Elected candidates detected:   {df['elected'].sum()}")

    other_strings = df.loc[df['party'] == 'other', 'candidate_raw'].unique()
    print(f"\n'other' party strings ({len(other_strings)} unique):")
    for s in other_strings[:10]:
        print(f"  {s}")
    if len(other_strings) > 10:
        print(f"  ... and {len(other_strings) - 10} more")

    # ── Insert into election_results ─────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Guard: don't double-import
    existing_2025 = c.execute(
        "SELECT COUNT(*) FROM election_results WHERE year = 2025"
    ).fetchone()[0]
    if existing_2025 > 0:
        print(f"\n{existing_2025} rows for 2025 already exist. "
              "Delete them first if you want to re-import.")
        conn.close()
        return

    df[['id', 'year', 'party', 'candidate', 'votecount', 'votepercent',
        'elected', 'incumbent', 'leanvsprovince', 'leanvsfederal']]\
        .to_sql('election_results', conn, if_exists='append', index=False)
    print(f"\nInserted {len(df)} rows into election_results (year=2025)")

    # ── Add voteshare2025 to electionresults ─────────────────────────────────
    existing_cols = [r[1] for r in c.execute(
        "PRAGMA table_info(electionresults)"
    ).fetchall()]
    if 'voteshare2025' not in existing_cols:
        c.execute("ALTER TABLE electionresults ADD COLUMN voteshare2025 REAL")

    total_votes = df['votecount'].sum()
    print("\n2025 national vote shares:")
    for code, label in PARTY_LABEL_MAP.items():
        share = round(df[df['party'] == code]['votecount'].sum() / total_votes * 100, 1)
        c.execute(
            "UPDATE electionresults SET voteshare2025 = ? WHERE upper(party) = ?",
            (share, label)
        )
        print(f"  {label}: {share}%")

    conn.commit()
    conn.close()
    print("\n2025 import complete.")
    print("\nVerify with:")
    print("  SELECT year, COUNT(*) FROM election_results GROUP BY year")
    print("  SELECT * FROM electionresults")


if __name__ == '__main__':
    main()
