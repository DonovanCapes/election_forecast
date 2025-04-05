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
os.chdir("C://projects//election_forecast")

start_time = time.time()

conn = sqlite3.connect('election_database/election_database.db')
c = conn.cursor()

######################################################################################################################
# Import 2021 election results
######################################################################################################################
results2021 = c.execute("SELECT party, voteshare2021 FROM electionresults")
election2021 = pd.DataFrame(results2021)
election2021 = dict(zip(election2021[0], election2021[1]))
election2021 = {k.lower(): v for k, v in election2021.items()}

######################################################################################################################
# Import riding results and Election Model variables
######################################################################################################################
nationaltable = c.execute("SELECT t1.id, t2.province, t2.riding_name, t1.party, t1.votepercent, t1.leanvsfederal FROM results2021 AS t1 JOIN ridings AS t2 ON t1.id = t2.id")
nationaldatabase = pd.DataFrame(nationaltable)

######################################################################################################################
# Create list of riding IDs
######################################################################################################################
ridingids = c.execute("SELECT DISTINCT id FROM results2021")
ridingidids = pd.DataFrame(ridingids)
ridingidlist = ridingidids[0].tolist()


######################################################################################################################
# Create DataFrame to store all election simulation results
######################################################################################################################
dfridingprobabilities = pd.DataFrame(index = ridingidlist, columns = ['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc'])
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
path = "C:/projects/election_forecast/model_results"

######################################################################################################################
# Monte Carlo Simulation
######################################################################################################################
# Function to account for margin of error
MarginOfError = weightavg('error')
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
    # Create DataFrame to store sim results
    dfelectionresults = pd.DataFrame(columns = ['lpc', 'cpc', 'ndp', 'gpc', 'bq', 'ppc'])
    dfridingpercentages = pd.DataFrame(columns = ['districtid', 'party', 'votepercent'])
    # Set win counts to zero
    lpc = cpc = ndp = gpc = bq = ppc = 0

    # iterate over the number of desired simulations
    for sim in range(numsims):
        # run single simulation
        lpcwins, cpcwins, ndpwins, gpcwins, bqwins, ppcwins, dfridingresults = SimulateElection()
        # add riding percentages to the master copy
        dfridingpercentages = pd.concat([dfridingpercentages, dfridingresults])       
        # create dict of parties and vote counts
        parties = {'lpc': lpcwins, 'cpc': cpcwins, 'ndp': ndpwins, 'gpc': gpcwins, 'bq': bqwins, 'ppc': ppcwins}
        # determine winner of simulation
        winner = max(parties, key = parties.get)
        # add results to elections DataFrame
        addrow = pd.DataFrame([{'lpc': lpcwins, 'cpc': cpcwins, 'ndp': ndpwins, 'gpc': gpcwins, 'bq': bqwins, 'ppc': ppcwins}])
        dfelectionresults = pd.concat([dfelectionresults, addrow], ignore_index = True)
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
    dfridingprobabilities = dfridingprobabilities.applymap(lambda x: round(x / numsims * 100, 1))

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
    k = p = 0
    # Create DataFrames to store riding results
    dfridingresults = pd.DataFrame(columns = ['districtid', 'party', 'votepercent'])

    # Perform on simulation for each riding
    for riding in ridingidlist:
        ridingid = ridingidlist[k]
        district = c.execute("SELECT * FROM results2021 WHERE id = ?", (ridingid, ))
        district = pd.DataFrame(district, columns = ['id', 'year', 'party', 'candidate', 'votecount', 'votepercent', 'elected',\
                                'incumbent', 'leanvsprovince', 'leanvsfederal'])
        
        resultsdict = {}

        # Variable for iterating within each district
        m = 0

        # Calculate election chances for each party
        for row in district.itertuples():
            
            try:
                party = row.party.lower() # get party name
                vote2021 = float(district['votepercent'][m]) # party vote in riding 
                partypoll = float(weightavg(party)) # current federal level party polling 
                pollwerr = AddErr(partypoll) # apply polling error (should this be at the federal level instead of each riding?)
                natvote = float(election2021[party]) # get national vote percentage from 2021
                propchange = (pollwerr - natvote) / natvote # calculate the proportion of change
                # distlean = float(district['leanvsfederal'][m])
                newvote = vote2021 + (propchange * vote2021) # recalculate the vote based on the proportion of change
                if newvote < 0:
                    newvote = 0
                
                # Compile results in DataFrame for export and analysis
                newrow = pd.DataFrame([{'districtid': ridingid, 'party': party, 'votepercent': newvote}])
                dfridingresults = pd.concat([dfridingresults,newrow], ignore_index = True)

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
            ppcwins += 1

        # Update global dataframe
        dfridingprobabilities.loc[dfridingprobabilities.index[p], winner] = \
            (dfridingprobabilities.loc[dfridingprobabilities.index[p], winner] + 1)
        p += 1
        
        # Tick up k variable
        k += 1

    # Normalize for 100% vote total
    dfridingresults['votepercent'] = (dfridingresults['votepercent'] / dfridingresults.groupby('districtid')['votepercent'].transform('sum')) * 100
    
    # Export election data as csv
    global n
    #filename = os.path.join(path, 'ridingsims' + str(n) +'.csv')
    #dfridingresults.to_csv(filename, index = False)
    print("Simulation #" + str(n) + ": complete")
    n += 1
    # Return the number of seats each party won
    return lpcwins, cpcwins, ndpwins, gpcwins, bqwins, ppcwins, dfridingresults


#SimulateElection()
SimulateMultipleElections(10)

######################################################################################################################
# Execute script to update seat projections
######################################################################################################################
#exec(open('SeatProjectionGraphs.py').read())

######################################################################################################################
# Update GeoJSON
######################################################################################################################
#os.chdir("C://Users//Donovan//Documents//Visual Studio Code//ElectoralMap")
#exec(open('exportgeojson.py').read())
