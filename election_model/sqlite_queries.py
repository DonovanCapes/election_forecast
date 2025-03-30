import sqlite3, csv, os, pathlib
import pandas as pd
#import numpy as np


######################################################################################################################
# Set directory, enable coding timer, and connect SQLite3 database
######################################################################################################################
os.chdir(r"C:\projects\election_forecast")

conn = sqlite3.connect('election_database\election_database.db')
c = conn.cursor()

drop = c.execute("DROP TABLE electionresults")

df_results_2021 = pd.read_csv('election_database/voteshare.csv')
print(df_results_2021)

df_results_2021.to_sql('electionresults', conn, index = False)

#conn = sqlite3.connect('election_database\election_database.db')

#df_polls = pd.read_csv('election_database/recent_polls_2025.csv')
#df_polls.to_sql('polls', conn, if_exists = 'append', index = False)
