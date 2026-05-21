######################################################################################################################
#
# Canadian Federal Election Forecast Model
# Author: Donovan Capes
# Created: 2020/09/07
# Last Edited: 2025/03/29
#
######################################################################################################################

######################################################################################################################
# Import libraries
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
# Import 2025 election results as national baseline
######################################################################################################################
results2025 = c.execute("SELECT party, voteshare2025 FROM federal_results")
election2021 = pd.DataFrame(results2025)
election2021 = dict(zip(election2021[0], election2021[1]))
election2021 = {k.lower(): v for k, v in election2021.items()}

######################################################################################################################
# Import riding results and Election Model variables
######################################################################################################################
nationaltable = c.execute("SELECT t1.id, t2.province, t2.riding_name, t1.party, t1.votepercent, t1.leanvsfederal FROM riding_results AS t1 JOIN ridings AS t2 ON t1.id = t2.id WHERE t1.year = 2025")
nationaldatabase = pd.DataFrame(nationaltable, columns=['id', 'province', 'riding_name', 'party', 'votepercent', 'leanvsfederal'])

######################################################################################################################
# Build riding lookup dict and riding ID list (avoids per-riding SQL queries during simulation)
######################################################################################################################
riding_data = {
    rid: list(zip(group['party'], group['votepercent'].astype(float)))
    for rid, group in nationaldatabase.groupby('id')
}
ridingidlist = list(riding_data.keys())


######################################################################################################################
# Create DataFrame to store all election simulation results
######################################################################################################################
dfridingprobabilities = pd.DataFrame(index = ridingidlist, columns = ['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc'])
dfridingprobabilities.index.name = 'FED_NUM'
dfridingprobabilities = dfridingprobabilities.fillna(0)

######################################################################################################################
# Import polling data from election_database.db
######################################################################################################################
pollsdict = c.execute("SELECT * FROM polls WHERE region = 'National'")
polls = pd.DataFrame(pollsdict, columns = ['region', 'lastdate', 'firm', 'method', 'sample', 'error', 'lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc'])
polls = polls.replace(r'^\s*$', 0, regex=True)

######################################################################################################################
# Set global variables for poll weighting
######################################################################################################################
weights = []
today = date.today()
today = datetime.strptime(str(today), "%Y-%m-%d")
polldate = datetime.strptime(polls['lastdate'][1], "%Y-%m-%d")
j = len(polls)

######################################################################################################################
# Calculate weighting off individual polls based on sample size and date
######################################################################################################################
for i in range(j):
    sizeweight = ((int(polls['sample'][i]) / 600) ** 0.5)
    polldate = datetime.strptime(polls['lastdate'][i], "%Y-%m-%d")
    datediff = abs((today - polldate).days)
    if int(datediff) < 8:
        totweight = sizeweight * 1
    elif 29 > int(datediff) > 7 :
        totweight = sizeweight * (1 - (0.047 * (int(datediff) - 7)))
    else:
        totweight = 0
    weights.append(round(totweight, 2))
polls['weight'] = weights

######################################################################################################################
# Function to apply poll weightings
######################################################################################################################
def weightavg(party):
    '''
    Calculates the weighted polling average for each party
    '''
    return round(np.average(polls[party].astype('float64'), weights= polls['weight'].astype('float64')), 1)

######################################################################################################################
# Global variables for storing model outputs
######################################################################################################################
n = 1
path = PROJECT_ROOT / 'model_results'

######################################################################################################################
# Monte Carlo Simulation
######################################################################################################################
# Function to account for margin of error
MarginOfError = weightavg('error')
poll_averages = {}
for _party in ['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc']:
    try:
        poll_averages[_party] = weightavg(_party)
    except Exception:
        poll_averages[_party] = 0.0

def AddErr(pollresult):
    '''
    Applies random error using a normal distribution and the weighted poll margin of error for each simulation
    '''
    x = np.random.normal() # generate normal distribution
    x = x/2 # 95% chance of x being between 1 and -1
    x = x * MarginOfError
    return x + pollresult # Apply margin of polling error

# Function to simulate multiple elections
def SimulateMultipleElections(numsims):
    '''
    Simulates multiple elections using the simulate election function
    '''
    # Collect results as lists; build DataFrames once after the loop (avoids O(n^2) pd.concat)
    election_rows = []
    riding_results_list = []
    # Set win counts to zero
    lpc = cpc = ndp = gpc = bq = ppc = 0

    # iterate over the number of desired simulations
    for sim in range(numsims):
        # run single simulation
        lpcwins, cpcwins, ndpwins, gpcwins, bqwins, ppcwins, dfridingresults = SimulateElection()
        # collect riding percentages
        riding_results_list.append(dfridingresults)
        # create dict of parties and vote counts
        parties = {'lpc': lpcwins, 'cpc': cpcwins, 'ndp': ndpwins, 'gpc': gpcwins, 'bq': bqwins, 'ppc': ppcwins}
        # determine winner of simulation
        winner = max(parties, key = parties.get)
        # collect election results
        election_rows.append({'lpc': lpcwins, 'cpc': cpcwins, 'ndp': ndpwins, 'gpc': gpcwins, 'bq': bqwins, 'ppc': ppcwins})
        # tick up win count for winner
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
    """
    # output probability of each party winning the most seats
    problpc = lpc / numsims
    probcpc = cpc / numsims
    probndp = ndp / numsims
    probgpc = gpc / numsims
    probbq = bq / numsims
    probppc = ppc / numsims

    probsrow = pd.DataFrame({'lpc': problpc, 'cpc': probcpc, 'ndp': probndp, 'gpc': probgpc, 'bq': probbq, 'ppc': probppc}, index = [0])
    dfelectionresults = pd.concat([probsrow, dfelectionresults[:]]).reset_index(drop = True)
    """
    
    # export overall election probability dataframe
    electionsimspath = os.path.join(path, 'seatcounts.csv')
    dfelectionresults.to_csv(electionsimspath, index = False)

    # calculate mean, max, and minimum seat counts
    seatprojectionstats = pd.DataFrame()
    seatprojectionstats['max'] = dfelectionresults.max()
    seatprojectionstats['min'] = dfelectionresults.min()
    seatprojectionstats['mean'] = dfelectionresults.mean()
    seatprojectionpath = os.path.join(path, 'seatstats.csv')
    seatprojectionstats.to_csv(seatprojectionpath, index = False)

    # calculate election odds for each party in each riding
    global dfridingprobabilities
    dfridingprobabilities = dfridingprobabilities.map(lambda x: round(x / numsims * 100, 1))

    # export riding probabilities dataframe
    ridingprobpath = os.path.join(path, 'ridingprobabilities.csv')
    dfridingprobabilities = dfridingprobabilities.rename(columns={'': 'FED_NUM', 'lpc': 'LPCwins', 'cpc': 'CPCwins', 'ndp': 'NDPwins', 'gpc': 'GPCwins', 'bq': 'BQwins', 'ppc': 'PPCwins'})
    dfridingprobabilities.to_csv(ridingprobpath, index = True)

    # calculate the average vote percentage for each party in each riding
    dfridingpercentagesavg = dfridingpercentages.groupby(['districtid', 'party']).mean()
    dfridingpercentagesavg = dfridingpercentagesavg.pivot_table(index = 'districtid', columns = 'party', values = 'votepercent')
    dfridingpercentagesavg = dfridingpercentagesavg.round(1)
    if "ppc" not in dfridingpercentagesavg:
        dfridingpercentagesavg['ppc'] = np.nan
    
    # calculate 2 standard deviations
    dfridingpercentagesstd = dfridingpercentages.groupby(['districtid', 'party']).std(ddof = 4)
    dfridingpercentagesstd = dfridingpercentagesstd.pivot_table(index = 'districtid', columns = 'party', values = 'votepercent')
    dfridingpercentagesstd = round(dfridingpercentagesstd * 2, 1)
    dfridingpercentagesstd = dfridingpercentagesstd.rename(columns = {'bq':'bqstd', 'cpc':'cpcstd', 'gpc':'gpcstd', 'lpc':'lpcstd', 'ndp':'ndpstd', 'ppc':'ppcstd'})
    masterdf = pd.merge(dfridingpercentagesavg, dfridingpercentagesstd, on = 'districtid', how = 'left')
    masterdf = masterdf.fillna(0)

   # export riding results
    ridingpercentpath = os.path.join(path, 'ridingvotepercents.csv')
    masterdf.to_csv(ridingpercentpath, index = True)

    print("Run time: %s seconds" % (time.time() - start_time))

######################################################################################################################
# Function to simulate a single election
######################################################################################################################
def SimulateElection():
    lpcwins = cpcwins = ndpwins = gpcwins = bqwins = ppcwins = 0
    p = 0
    # Collect rows as a list; build DataFrame once at end (avoids O(n^2) pd.concat)
    riding_rows = []

    # Perform one simulation for each riding
    for ridingid in ridingidlist:
        resultsdict = {}

        # Calculate election chances for each party using pre-loaded riding data
        for party, vote2025 in riding_data[ridingid]:
            try:
                party = party.lower()
                partypoll = poll_averages[party] # pre-computed weighted polling average
                pollwerr = AddErr(partypoll) # apply polling error
                natvote = float(election2021[party]) # national vote percentage from 2025 baseline
                propchange = (pollwerr - natvote) / natvote # proportion of change
                newvote = vote2025 + (propchange * vote2025) # recalculate vote
                if newvote < 0:
                    newvote = 0

                riding_rows.append({'districtid': ridingid, 'party': party, 'votepercent': newvote})
                resultsdict[party] = newvote

            except:
                continue

        # Determine riding winner
        winner = max(resultsdict, key = resultsdict.get)
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

        # Update global dataframe
        dfridingprobabilities.loc[dfridingprobabilities.index[p], winner] = \
            (dfridingprobabilities.loc[dfridingprobabilities.index[p], winner] + 1)
        p += 1

    # Build results DataFrame and normalize to 100% vote total per riding
    dfridingresults = pd.DataFrame(riding_rows, columns=['districtid', 'party', 'votepercent'])
    dfridingresults['votepercent'] = (dfridingresults['votepercent'] / dfridingresults.groupby('districtid')['votepercent'].transform('sum')) * 100

    global n
    print("Simulation #" + str(n) + ": complete")
    n += 1
    return lpcwins, cpcwins, ndpwins, gpcwins, bqwins, ppcwins, dfridingresults


#SimulateElection()
SimulateMultipleElections(10000)

######################################################################################################################
# Execute script to update seat projections
######################################################################################################################
#exec(open('SeatProjectionGraphs.py').read())

######################################################################################################################
# Update GeoJSON
######################################################################################################################
#os.chdir("C://Users//Donovan//Documents//Visual Studio Code//ElectoralMap")
#exec(open('exportgeojson.py').read())
