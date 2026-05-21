"""
scrape_polls.py - Scrapes national polling data from 338canada.com/polls.htm
and inserts new polls into the polls table.

Designed to run daily as part of the automated pipeline. Checks existing
(firm, lastdate) pairs before inserting so re-runs are safe.

Run from the project root:
    .venv/Scripts/python.exe election_database/scrape_polls.py
"""

import json
import math
import re
import sqlite3
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / 'election_database' / 'election_database.db'
URL = "https://338canada.com/polls.htm"

# Fixed cell order on 338Canada: LPC, CPC, NDP, GPC, BQ
# Validated against background colours: #d90000, #e2e2ff, #ffeac4, #ddf7dd, #e7f8ff
CELL_ORDER = ["lpc", "cpc", "ndp", "gpc", "bq"]

# Expected background colours per party — used to validate page structure hasn't changed
EXPECTED_COLORS = {
    0: "#d90000",  # LPC red
    1: "#e2e2ff",  # CPC blue
    2: "#ffeac4",  # NDP orange
    3: "#ddf7dd",  # GPC green
    4: "#e7f8ff",  # BQ cyan
}


def fetch_raw_poll_rows():
    """Fetch the page and extract the national poll rows from the JS data object."""
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()

    match = re.search(
        r"window\.demopoll_TABLE_DATA\s*=\s*(\{.*?\});\s*\n",
        r.text,
        re.DOTALL,
    )
    if not match:
        raise ValueError(
            "demopoll_TABLE_DATA not found — page structure may have changed"
        )

    data = json.loads(match.group(1))
    return data["demos"]["National"]["rows"]


def validate_cell_order(row):
    """Check the first row's cell colours match expectations. Warns if the page layout changed."""
    for idx, cell in enumerate(row["cells"]):
        expected = EXPECTED_COLORS.get(idx)
        if expected and cell["background"] != expected:
            print(
                f"WARNING: Cell {idx} background is {cell['background']!r}, "
                f"expected {expected!r}. Party order may have changed — review scraper."
            )


def parse_sample(sample_str):
    return int(sample_str.replace(",", "").strip())


def calc_moe(sample):
    """95% confidence interval margin of error from sample size."""
    return round(1.96 / math.sqrt(sample) * 100, 1)


def parse_row(row):
    sample = parse_sample(row["sample"])
    cells = row["cells"]

    shares = {}
    for idx, party in enumerate(CELL_ORDER):
        if idx < len(cells):
            try:
                shares[party] = float(cells[idx]["label"])
            except (ValueError, KeyError):
                shares[party] = None

    return {
        "region": "National",
        "lastdate": row["date"],
        "firm": row["firm"],
        "method": None,       # not provided by 338Canada
        "sample": sample,
        "error": calc_moe(sample),
        "lpc": shares.get("lpc"),
        "cpc": shares.get("cpc"),
        "ndp": shares.get("ndp"),
        "gpc": shares.get("gpc"),
        "bq": shares.get("bq"),
        "ppc": None,          # not tracked by 338Canada post-2025 election
    }


def main():
    print(f"Fetching polls from {URL} ...")
    raw_rows = fetch_raw_poll_rows()
    print(f"Found {len(raw_rows)} national polls on page")

    # Validate cell order on first row
    if raw_rows:
        validate_cell_order(raw_rows[0])

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    existing = set(
        c.execute("SELECT firm, lastdate FROM polls").fetchall()
    )
    print(f"Existing polls in DB: {len(existing)}")

    inserted = 0
    skipped = 0
    errors = 0

    for row in raw_rows:
        # Skip election result rows (generalelx is non-empty for these)
        if row.get("generalelx"):
            skipped += 1
            continue

        try:
            poll = parse_row(row)
        except Exception as e:
            print(f"  Error parsing row {row.get('date')} / {row.get('firm')}: {e}")
            errors += 1
            continue

        key = (poll["firm"], poll["lastdate"])
        if key in existing:
            skipped += 1
            continue

        c.execute(
            """
            INSERT INTO polls (region, lastdate, firm, method, sample, error,
                               lpc, cpc, ndp, gpc, bq, ppc)
            VALUES (:region, :lastdate, :firm, :method, :sample, :error,
                    :lpc, :cpc, :ndp, :gpc, :bq, :ppc)
            """,
            poll,
        )
        existing.add(key)
        inserted += 1

    conn.commit()
    conn.close()

    print(f"Done: {inserted} inserted, {skipped} already in DB, {errors} errors")
    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
