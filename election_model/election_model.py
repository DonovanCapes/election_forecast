######################################################################################################################
#
# Canadian Federal Election Forecast Model
# Author: Donovan Capes
# Created: 2020/09/07
# Last Edited: 2021/04/18
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
os.chdir(r"C:\Users\Donovan\Documents\Visual Studio Code\ElectionModel")

start_time = time.time()

conn = sqlite3.connect('ElectionModel.db')
c = conn.cursor()

######################################################################################################################
# Import 2019 election results
######################################################################################################################
results2019 = c.execute("SELECT party, votepercent2019 FROM electionresults")
election2019 = pd.DataFrame(results2019)
election2019 = dict(zip(election2019[0], election2019[1]))
election2019 = {k.lower(): v for k, v in election2019.items()}

######################################################################################################################
# Import riding results and Election Model variables
######################################################################################################################
nationaltable = c.execute("SELECT t1.id, t2.province, t2.riding, t1.party, t1.votepercentage, t1.leanvsfederal FROM results2019 AS t1 JOIN ridings AS t2 ON t1.id = t2.id")
nationaldatabase = pd.DataFrame(nationaltable)

######################################################################################################################
# Create list of riding IDs
######################################################################################################################
ridingids = c.execute("SELECT DISTINCT id FROM results2019")
ridingidids = pd.DataFrame(ridingids)
ridingidlist = ridingidids[0].tolist()

######################################################################################################################
# Create DataFrame to store all election simulation results
######################################################################################################################
dfridingprobabilities = pd.DataFrame(index = ridingidlist, columns = ['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'other'])
dfridingprobabilities = dfridingprobabilities.fillna(0)

######################################################################################################################
# Import polling data from ElectionModel.db
######################################################################################################################
pollsdict = c.execute("SELECT * FROM polls WHERE region = 'National'")
polls = pd.DataFrame(pollsdict, columns = ['region', 'lastdate', 'firm', 'method', 'sample', 'error', 'lpc', 'cpc', 'ndp', 'gpc', 'bq', 'other'])
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
# Apply weighting to polls and final output
######################################################################################################################
def weightavg(party):
    return round(np.average(polls[party].astype('float64'), weights= polls['weight'].astype('float64')), 1)

######################################################################################################################
# Global variables for storing model outputs
######################################################################################################################
n = 1
path = "C:/Users/Donovan/Documents/Visual Studio Code/ElectionModel/SimResults"

######################################################################################################################
# Monte Carlo Simulation
######################################################################################################################
# Function to account for margin of error
MarginOfError = weightavg('error')
def AddErr(pollresult):
    x = np.random.normal() # generate normal distribution
    x = x/2 # 95% chance of x being between 1 and -1
    x = x * MarginOfError
    return x + pollresult # Apply margin of polling error

# Function to simulate multiple elections
def SimulateMultipleElections(numsims):

    # Create DataFrame to store sim results
    dfelectionresults = pd.DataFrame(columns = ['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'other'])
    dfridingpercentages = pd.DataFrame(columns = ['districtid', 'party', 'votepercentage'])
    # Set win counts to zero
    lpc = cpc = ndp = gpc = bq = other = 0

    # iterate over the number of desired simulations
    for sim in range(numsims):
        # run single simulation
        lpcwins, cpcwins, ndpwins, gpcwins, bqwins, otherwins, dfridingresults = SimulateElection()
        # add riding percentages to the master copy
        dfridingpercentages = dfridingpercentages.append(dfridingresults)       
        # create dict of parties and vote counts
        parties = {'lpc': lpcwins, 'cpc': cpcwins, 'ndp': ndpwins, 'gpc': gpcwins, 'bq': bqwins, 'other': otherwins}
        # determine winner of simulation
        winner = max(parties, key = parties.get)
        # add results to elections DataFrame
        addrow = [{'lpc': lpcwins, 'cpc': cpcwins, 'ndp': ndpwins, 'gpc': gpcwins, 'bq': bqwins, 'other': otherwins}]
        dfelectionresults = dfelectionresults.append(addrow, ignore_index = True)
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
            other += 1
    """
    # output probability of each party winning the most seats
    problpc = lpc / numsims
    probcpc = cpc / numsims
    probndp = ndp / numsims
    probgpc = gpc / numsims
    probbq = bq / numsims
    probother = other / numsims

    probsrow = pd.DataFrame({'lpc': problpc, 'cpc': probcpc, 'ndp': probndp, 'gpc': probgpc, 'bq': probbq, 'other': probother}, index = [0])
    dfelectionresults = pd.concat([probsrow, dfelectionresults[:]]).reset_index(drop = True)
    """
    
    # export overall election probability dataframe
    electionsimspath = os.path.join(path, 'seatcounts.csv')
    dfelectionresults.to_csv(electionsimspath, index = False)

    # calculate mean, max, and minimum seat counts
    seatprojectionstats = pd.DataFrame()
    seatprojectionstats['Max'] = round(dfelectionresults.max(), 0)
    seatprojectionstats['Min'] = round(dfelectionresults.min(), 0)
    seatprojectionstats['Mean'] = round(dfelectionresults.mean(), 0)
    seatprojectionpath = os.path.join(path, 'seatstats.csv')
    seatprojectionstats.to_csv(seatprojectionpath, index = False)

    # calculate election odds for each party in each riding
    global dfridingprobabilities
    dfridingprobabilities = dfridingprobabilities.applymap(lambda x: round(x / numsims * 100, 1))

    # export riding probabilities dataframe
    ridingprobpath = os.path.join(path, 'ridingprobabilities.csv')
    dfridingprobabilities.to_csv(ridingprobpath, index = True)

    # calculate the average vote percentage for each party in each riding
    dfridingpercentagesavg = dfridingpercentages.groupby(['districtid', 'party']).mean()
    dfridingpercentagesavg = dfridingpercentagesavg.pivot_table(index = 'districtid', columns = 'party', values = 'votepercentage')
    dfridingpercentagesavg = dfridingpercentagesavg.round(1)
    if "other" not in dfridingpercentagesavg:
        dfridingpercentagesavg['other'] = np.nan
    
    # calculate 2 standard deviations
    dfridingpercentagesstd = dfridingpercentages.groupby(['districtid', 'party']).std(ddof = 4)
    dfridingpercentagesstd = dfridingpercentagesstd.pivot_table(index = 'districtid', columns = 'party', values = 'votepercentage')
    dfridingpercentagesstd = round(dfridingpercentagesstd * 2, 1)
    dfridingpercentagesstd = dfridingpercentagesstd.rename(columns = {'bq':'bqstd', 'cpc':'cpcstd', 'gpc':'gpcstd', 'lpc':'lpcstd', 'ndp':'ndpstd'})
    masterdf = pd.merge(dfridingpercentagesavg, dfridingpercentagesstd, on = 'districtid', how = 'left')
    masterdf = masterdf.fillna(0)

   # export riding results
    ridingpercentpath = os.path.join(path, 'ridingvotepercentages.csv')
    masterdf.to_csv(ridingpercentpath, index = True)

    print("Run time: %s seconds" % (time.time() - start_time))

######################################################################################################################
# Function to simulate a single election
######################################################################################################################
def SimulateElection():
    lpcwins = cpcwins = ndpwins = gpcwins = bqwins = otherwins = 0
    k = p = 0
    # Create DataFrames to store riding results
    dfridingresults = pd.DataFrame(columns = ['districtid', 'party', 'votepercentage'])

    # Perform on simulation for each riding
    for riding in ridingidlist:
        ridingid = ridingidlist[k]
        district = c.execute("SELECT * FROM results2019 WHERE id = ?", (ridingid, ))
        district = pd.DataFrame(district, columns = ['id', 'year', 'party', 'candidate', 'votecount', 'votepercentage', 'elected',\
                                'incumbent', 'leanvsprovince', 'leanvsfederal'])
        
        resultsdict = {}

        # Variable for iterating within each districts
        m = 0

        # Calculate election chances for each party
        for row in district.itertuples():
            try:
                party = row.party
                party = party.lower()
                vote2019 = float(district['votepercentage'][m])
                partypoll = float(weightavg(party))
                pollwerr = AddErr(partypoll)
                natvote = float(election2019[party])
                propchange = (pollwerr - natvote) / natvote
                # distlean = float(district['leanvsfederal'][m])
                newvote = vote2019 + (propchange * vote2019)
                if newvote < 0:
                    newvote = 0
                
                # Compile results in DataFrame for export and analysis
                newrow = [{'districtid': ridingid, 'party': party, 'votepercentage': newvote}]
                dfridingresults = dfridingresults.append(newrow, ignore_index = True)

                # Add each party's chances in riding to dict
                resultsdict[party] = newvote

                # Tick up variable
                m += 1
                
            except:
                m += 1
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
            otherwins += 1

        # Update global dataframe
        dfridingprobabilities.loc[dfridingprobabilities.index[p], winner] = \
            (dfridingprobabilities.loc[dfridingprobabilities.index[p], winner] + 1)
        p += 1
        
        # Tick up k variable
        k += 1

    # Normalize for 100% vote total
    dfridingresults['votepercentage'] = (dfridingresults['votepercentage'] / dfridingresults.groupby('districtid')['votepercentage'].transform('sum')) * 100
    
    # Export election data as csv
    global n
    filename = os.path.join(path, 'ridingsims' + str(n) +'.csv')
    #dfridingresults.to_csv(filename, index = False)
    print("Simulation #" + str(n) + ": complete")
    n += 1
    # Return the number of seats each party won
    return lpcwins, cpcwins, ndpwins, gpcwins, bqwins, otherwins, dfridingresults

SimulateMultipleElections(10000)

######################################################################################################################
# Execute script to update seat projections
######################################################################################################################
exec(open('SeatProjectionGraphs.py').read())

######################################################################################################################
# Update GeoJSON
######################################################################################################################
os.chdir(r"C:\Users\Donovan\Documents\Visual Studio Code\ElectoralMap")
exec(open('exportgeojson.py').read())