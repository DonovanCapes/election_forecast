######################################################################################################################
#
# Canadian Federal Election Forecast Model — Weighted Baseline
# Author: Donovan Capes
#
# Variant of election_model.py that uses a weighted multi-election riding baseline:
#   2025 = 60%, 2021 = 30%, 2019 = 10%
# For the 5 ridings with no 2019 data (new boundaries), the 10% weight rolls into 2025 (70/30).
#
######################################################################################################################

import sqlite3, csv, os, pathlib, time
import pandas as pd
import numpy as np

from datetime import date, datetime

######################################################################################################################
# Set directory, enable coding timer, and connect SQLite3 database
######################################################################################################################
PROJECT_ROOT = pathlib.Path(__file__).parent.parent

start_time = time.time()

conn = sqlite3.connect(PROJECT_ROOT / 'election_database' / 'election_database.db')
c = conn.cursor()

######################################################################################################################
# Build weighted national baseline from federal_results
######################################################################################################################
fed = pd.DataFrame(
    c.execute("SELECT party, voteshare2019, voteshare2021, voteshare2025 FROM federal_results"),
    columns=['party', 'vs2019', 'vs2021', 'vs2025']
)
fed['party'] = fed['party'].str.lower()
fed['weighted'] = 0.6 * fed['vs2025'] + 0.3 * fed['vs2021'] + 0.1 * fed['vs2019']
national_baseline = dict(zip(fed['party'], fed['weighted']))

######################################################################################################################
# Build weighted riding baseline from riding_results (2025, 2021, 2019)
######################################################################################################################
def fetch_riding_year(year):
    rows = c.execute(
        "SELECT t1.id, t2.province, t2.riding_name, t1.party, t1.votepercent "
        "FROM riding_results AS t1 JOIN ridings AS t2 ON t1.id = t2.id "
        "WHERE t1.year = ?", (year,)
    )
    return pd.DataFrame(rows, columns=['id', 'province', 'riding_name', 'party', 'votepercent'])

df2025 = fetch_riding_year(2025)
df2021 = fetch_riding_year(2021)[['id', 'party', 'votepercent']].rename(columns={'votepercent': 'vp2021'})
df2019 = fetch_riding_year(2019)[['id', 'party', 'votepercent']].rename(columns={'votepercent': 'vp2019'})

nationaldatabase = (
    df2025
    .merge(df2021, on=['id', 'party'], how='left')
    .merge(df2019, on=['id', 'party'], how='left')
)

# For ridings missing 2019 data (5 new ridings), fall back to 2025 value so weights remain valid
nationaldatabase['vp2019'] = nationaldatabase['vp2019'].fillna(nationaldatabase['votepercent'])
nationaldatabase['vp2021'] = nationaldatabase['vp2021'].fillna(nationaldatabase['votepercent'])

nationaldatabase['votepercent'] = (
    0.6 * nationaldatabase['votepercent']
    + 0.3 * nationaldatabase['vp2021']
    + 0.1 * nationaldatabase['vp2019']
)

######################################################################################################################
# Build riding lookup dict and riding ID list
######################################################################################################################
riding_data = {
    rid: list(zip(group['party'], group['votepercent'].astype(float)))
    for rid, group in nationaldatabase.groupby('id')
}
ridingidlist = list(riding_data.keys())

######################################################################################################################
# Create DataFrame to store all election simulation results
######################################################################################################################
dfridingprobabilities = pd.DataFrame(index=ridingidlist, columns=['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc'])
dfridingprobabilities.index.name = 'FED_NUM'
dfridingprobabilities = dfridingprobabilities.fillna(0)

######################################################################################################################
# Import polling data
######################################################################################################################
pollsdict = c.execute("SELECT * FROM polls WHERE region = 'National'")
polls = pd.DataFrame(pollsdict, columns=['region', 'lastdate', 'firm', 'method', 'sample', 'error', 'lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc'])
polls = polls.replace(r'^\s*$', 0, regex=True)

######################################################################################################################
# Poll weighting by recency and sample size
######################################################################################################################
weights = []
today = date.today()
today = datetime.strptime(str(today), "%Y-%m-%d")

for i in range(len(polls)):
    sizeweight = (int(polls['sample'][i]) / 600) ** 0.5
    polldate = datetime.strptime(polls['lastdate'][i], "%Y-%m-%d")
    datediff = abs((today - polldate).days)
    if datediff < 8:
        totweight = sizeweight * 1
    elif 29 > datediff > 7:
        totweight = sizeweight * (1 - (0.047 * (datediff - 7)))
    else:
        totweight = 0
    weights.append(round(totweight, 2))
polls['weight'] = weights

######################################################################################################################
# Weighted polling average
######################################################################################################################
def weightavg(party):
    return round(np.average(polls[party].astype('float64'), weights=polls['weight'].astype('float64')), 1)

######################################################################################################################
# Pre-compute poll averages and margin of error
######################################################################################################################
MarginOfError = weightavg('error')
poll_averages = {}
for _party in ['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc']:
    try:
        poll_averages[_party] = weightavg(_party)
    except Exception:
        poll_averages[_party] = 0.0

n = 1
path = PROJECT_ROOT / 'model_results'
path.mkdir(exist_ok=True)

######################################################################################################################
# Monte Carlo simulation
######################################################################################################################
def AddErr(pollresult):
    x = np.random.normal() / 2 * MarginOfError
    return x + pollresult


def SimulateElection():
    global n
    lpcwins = cpcwins = ndpwins = gpcwins = bqwins = ppcwins = 0
    p = 0
    riding_rows = []

    for ridingid in ridingidlist:
        resultsdict = {}

        for party, weighted_base in riding_data[ridingid]:
            try:
                party = party.lower()
                partypoll = poll_averages[party]
                pollwerr = AddErr(partypoll)
                natvote = float(national_baseline[party])
                propchange = (pollwerr - natvote) / natvote
                newvote = weighted_base + (propchange * weighted_base)
                if newvote < 0:
                    newvote = 0

                riding_rows.append({'districtid': ridingid, 'party': party, 'votepercent': newvote})
                resultsdict[party] = newvote

            except Exception:
                continue

        winner = max(resultsdict, key=resultsdict.get)
        if winner == 'lpc':
            lpcwins += 1
        elif winner == 'cpc':
            cpcwins += 1
        elif winner == 'ndp':
            ndpwins += 1
        elif winner == 'gpc':
            gpcwins += 1
        elif winner == 'bq':
            bqwins += 1
        else:
            ppcwins += 1

        dfridingprobabilities.loc[dfridingprobabilities.index[p], winner] += 1
        p += 1

    dfridingresults = pd.DataFrame(riding_rows, columns=['districtid', 'party', 'votepercent'])
    dfridingresults['votepercent'] = (
        dfridingresults['votepercent']
        / dfridingresults.groupby('districtid')['votepercent'].transform('sum')
        * 100
    )

    print(f"Simulation #{n}: complete")
    n += 1
    return lpcwins, cpcwins, ndpwins, gpcwins, bqwins, ppcwins, dfridingresults


def SimulateMultipleElections(numsims):
    election_rows = []
    riding_results_list = []
    lpc = cpc = ndp = gpc = bq = ppc = 0

    for sim in range(numsims):
        lpcwins, cpcwins, ndpwins, gpcwins, bqwins, ppcwins, dfridingresults = SimulateElection()
        riding_results_list.append(dfridingresults)
        parties = {'lpc': lpcwins, 'cpc': cpcwins, 'ndp': ndpwins, 'gpc': gpcwins, 'bq': bqwins, 'ppc': ppcwins}
        winner = max(parties, key=parties.get)
        election_rows.append(parties)
        if winner == 'lpc':
            lpc += 1
        elif winner == 'cpc':
            cpc += 1
        elif winner == 'ndp':
            ndp += 1
        elif winner == 'gpc':
            gpc += 1
        elif winner == 'bq':
            bq += 1
        else:
            ppc += 1

    dfelectionresults = pd.DataFrame(election_rows)
    dfridingpercentages = pd.concat(riding_results_list, ignore_index=True)

    dfelectionresults.to_csv(path / 'seatcounts.csv', index=False)

    seatprojectionstats = pd.DataFrame()
    seatprojectionstats['max'] = dfelectionresults.max()
    seatprojectionstats['min'] = dfelectionresults.min()
    seatprojectionstats['mean'] = dfelectionresults.mean()
    seatprojectionstats.to_csv(path / 'seatstats.csv', index=False)

    global dfridingprobabilities
    dfridingprobabilities = dfridingprobabilities.map(lambda x: round(x / numsims * 100, 1))
    dfridingprobabilities = dfridingprobabilities.rename(columns={
        'lpc': 'LPCwins', 'cpc': 'CPCwins', 'ndp': 'NDPwins',
        'gpc': 'GPCwins', 'bq': 'BQwins', 'ppc': 'PPCwins'
    })
    dfridingprobabilities.index.name = 'FED_NUM'
    dfridingprobabilities.to_csv(path / 'ridingprobabilities.csv', index=True)

    dfridingpercentagesavg = (
        dfridingpercentages.groupby(['districtid', 'party'])['votepercent']
        .mean()
        .unstack('party')
        .round(1)
    )
    if 'ppc' not in dfridingpercentagesavg:
        dfridingpercentagesavg['ppc'] = np.nan

    dfridingpercentagesstd = (
        dfridingpercentages.groupby(['districtid', 'party'])['votepercent']
        .std(ddof=4)
        .unstack('party')
        .mul(2)
        .round(1)
    )

    # Cap each std at the party's mean so the lower bound never goes below 0
    for party in dfridingpercentagesstd.columns:
        if party in dfridingpercentagesavg.columns:
            dfridingpercentagesstd[party] = dfridingpercentagesstd[party].clip(upper=dfridingpercentagesavg[party])

    dfridingpercentagesstd = dfridingpercentagesstd.rename(
        columns={'bq': 'bqstd', 'cpc': 'cpcstd', 'gpc': 'gpcstd',
                 'lpc': 'lpcstd', 'ndp': 'ndpstd', 'ppc': 'ppcstd'}
    )

    masterdf = dfridingpercentagesavg.merge(dfridingpercentagesstd, on='districtid', how='left').fillna(0)
    masterdf.to_csv(path / 'ridingvotepercents.csv', index=True)

    print("Run time: %s seconds" % (time.time() - start_time))


SimulateMultipleElections(10000)
