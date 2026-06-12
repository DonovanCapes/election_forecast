# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the pipeline

All scripts use `os.chdir("C://projects//election_forecast")` and must be run from the project root. Use the local venv:

```powershell
# Run the forecast model — weighted baseline: 2025=60%, 2021=30%, 2019=10% (primary)
.venv/Scripts/python.exe election_model/election_model_weighted.py

# Run the forecast model — pure 2025 baseline (for comparison)
.venv/Scripts/python.exe election_model/election_model.py

# Rebuild the GeoJSON from model outputs
.venv/Scripts/python.exe election_map/create_geojson.py

# Generate a standalone Folium HTML map (outputs election_map/index.html)
.venv/Scripts/python.exe election_map/generate_election_map_html.py
```

To load polls into the database, uncomment and adapt the relevant block in `election_model/sqlite_queries.py` (it is gitignored).

## Architecture

The pipeline runs in four sequential stages:

```
[SQLite DB] -> election_model.py -> model_results/ CSVs -> create_geojson.py -> election_forecast_2025.geojson -> Jekyll site
```

**Stage 1 — Database (`election_database/election_database.db`)**
Single SQLite file. Key tables:

- `ridings` — master list of ridings (`id`, `province`, `riding_name`, `redistricting_year`). Current 343 ridings have `redistricting_year = 2022`. When boundaries are redrawn, new rows are inserted with the new redistricting year; historical rows are kept for reference. The 338-riding era (2015–2021, `redistricting_year = 2012`) is not yet loaded.
- `riding_results` — per-riding per-party results for all election years in a single table (`id`, `year`, `party`, `candidate`, `votecount`, `votepercent`, `elected`, `incumbent`, `leanvsprovince`, `leanvsfederal`). Contains 2015, 2019, 2021, and 2025 data. Query by `year` to isolate a specific election.
- `federal_results` — national vote shares by election year (`party`, `voteshare2015`, `voteshare2019`, `voteshare2021`, `voteshare2025`). Party codes are uppercase (LPC, CPC, NDP, GPC, BQ, PPC). Used by the model as the national baseline.
- `polls` — polling inputs (`region`, `lastdate`, `firm`, `method`, `sample`, `error`, party share columns). The model filters to `region = 'National'`.

**Stage 2 — Model (`election_model/election_model.py`)**
Loads polls, weights them by recency (full weight <=7 days, linear decay to zero at 29 days) and sample size (sqrt(n/600)), then runs `SimulateMultipleElections(10000)`. Each simulation calls `SimulateElection()`, which applies a multiplicative national swing to every riding's baseline:

```python
propchange = (pollWithError - national_baseline) / national_baseline
newvote = riding_baseline + (propchange * riding_baseline)
```

Error is injected per-party per-simulation via `AddErr()`, sampling from `Normal(0,1)/2 * weightedMoE`.

Two model variants exist: `election_model_weighted.py` (primary — weighted baseline: 2025=60%, 2021=30%, 2019=10%) and `election_model.py` (pure 2025 baseline, kept for comparison). For the 5 new ridings with no 2019 data, the 10% rolls into 2025 (70/30 split). Both write to the same `model_results/` outputs.

Outputs four CSVs to `model_results/`: `ridingvotepercents.csv`, `ridingprobabilities.csv`, `seatcounts.csv`, `seatstats.csv`.

**Stage 3 — GeoJSON (`election_map/create_geojson.py`)**
Merges `model_results/ridingvotepercents.csv` and `ridingprobabilities.csv` onto the base boundary file `election_map/electoral_districts_2022_fed.geojson` (join key: `FED_NUM`). Assigns a `Fill` colour per riding based on projected winner and win-probability margin (4 shades per party). Writes to `election_map/election_forecast_2025.geojson`.

**Stage 4 — Jekyll site (`C:/projects/donovancapes.github.io`)**
The GeoJSON and `ridingvotepercents.csv` are manually copied to the site repo. The Leaflet map in `_includes/election_map.html` loads the GeoJSON directly; the per-province riding tables are driven by `assets/js/election-forecast-enhanced.js` reading `assets/data/ridingvotepercents.csv`.

## Database migration scripts

One-time scripts in `election_database/` document how the schema was built:

- `migrate_schema.py` — merged `results2015/2019/2021` into `riding_results`, dropped stale tables
- `import_2025_results.py` — cleaned and loaded `2025_fed_election_results.csv` into `riding_results`, populated `federal_results.voteshare2025`
- `cleanup_db.py` — renamed tables to final names, dropped `diff` column, added `redistricting_year` to `ridings`

## Gitignore notes

All `.csv`, `.json`, and `.geojson` files are gitignored in this repo, as are `sqlite_queries.py` and `election_map/ridings.db`. Model outputs and data files must be transferred to the site repo manually.
