import sqlite3
import os
import csv
import geojson
import geopandas
from shapely.geometry import Polygon
from shapely.geometry import Point
import pandas as pd
import numpy as np
import re
from datetime import date

os.chdir(r"C:\Users\Donovan\Documents\Visual Studio Code\ElectoralMap")

# Import Elections Canada geojson
gdf = geopandas.read_file('2019ridingboundaries.geojson')
# Split Description column
gdf[['0', '1','2','3','4','5','6','7','8','9','10','11','12','13']] = gdf.description.str.split("|", expand = True)
# Delete unneccessary information
gdf = gdf.drop(columns=['title','description','fill','0','1','3','4','7','8','9','10','11','12','13'])
# Rename columns
gdf = gdf.rename(columns = {'2':'FEDNUM', '5':'Riding', '6':'Province'})
# Delete extra text in remaining columns
gdf['FEDNUM'] = gdf['FEDNUM'].str.extract(r'(\d+)', expand=False)
gdf['Riding'] = gdf['Riding'].str.extract(r'(.*) ', expand=False)
gdf['Province'] = gdf['Province'].str.extract(r'(.*) ', expand=False)
# Convert FEDNUM to int datatype
gdf['FEDNUM'] = gdf['FEDNUM'].astype(int)

# Read in riding election probabilities
probs = pd.read_csv(r"C:\Users\Donovan\Documents\Visual Studio Code\ElectionModel\SimResults\ridingprobabilities.csv")
# Rename ridingid to FEDNUM for merge
probs = probs.rename(columns = {list(probs)[0]:"FEDNUM"})
# Merge
df = gdf.merge(probs, on='FEDNUM', how='left')
gdf = geopandas.GeoDataFrame(df)
# Capitalize Party names
gdf = gdf.rename(columns = {'lpc':'LPCwins', 'cpc':'CPCwins', 'ndp':'NDPwins', 'gpc':'GPCwins', 'bq':'BQwins', 'other':'Otherwins'})

# Asign colours based on most likely winner
# Set Party columns to numeric
gdf['LPCwins'] = pd.to_numeric(gdf['LPCwins'])
gdf['CPCwins'] = pd.to_numeric(gdf['CPCwins'])
gdf['NDPwins'] = pd.to_numeric(gdf['NDPwins'])
gdf['GPCwins'] = pd.to_numeric(gdf['GPCwins'])
gdf['BQwins'] = pd.to_numeric(gdf['BQwins'])
gdf['Otherwins'] = pd.to_numeric(gdf['Otherwins'])

# Create columns for winning Party and probability
gdf['Winner'] = ''
gdf['Margin'] = ''
margin = gdf[['LPCwins', 'CPCwins', 'NDPwins', 'GPCwins', 'BQwins', 'Otherwins']]
gdf['Winner'] = margin.idxmax(axis=1)
gdf['Margin'] = margin.max(axis=1)

gdf = geopandas.GeoDataFrame(gdf)

# Create function and iterate over each row to populate Colour Fill column
def colindex(x):
    if (x['Winner'] == 'CPCwins') and (x['Margin'] <= 40):
        return '#e6e6ff'
    elif (x['Winner'] == 'CPCwins') and (x['Margin'] > 40) and (x['Margin'] <= 60):
        return'#9999ff'
    elif (x['Winner'] == 'CPCwins') and (x['Margin'] > 60) and (x['Margin'] <= 80):
        return '#4d4dff'
    elif (x['Winner'] == 'CPCwins') and (x['Margin'] > 80) and (x['Margin'] <= 100):
        return '#0000ff'
    elif (x['Winner'] == 'LPCwins') and (x['Margin'] <= 40):
        return '#ffe6e6'
    elif (x['Winner'] == 'LPCwins') and (x['Margin'] > 40) and (x['Margin'] <= 60):
        return'#ff9999'
    elif (x['Winner'] == 'LPCwins') and (x['Margin'] > 60) and (x['Margin'] <= 80):
        return '#ff4d4d'
    elif (x['Winner'] == 'LPCwins') and (x['Margin'] > 80) and (x['Margin'] <= 100):
        return '#ff0000'
    elif (x['Winner'] == 'NDPwins') and (x['Margin'] <= 40):
        return '#fff5e6'
    elif (x['Winner'] == 'NDPwins') and (x['Margin'] > 40) and (x['Margin'] <= 60):
        return'#ffd699'
    elif (x['Winner'] == 'NDPwins') and (x['Margin'] > 60) and (x['Margin'] <= 80):
        return '#ffb84d'
    elif (x['Winner'] == 'NDPwins') and (x['Margin'] > 80) and (x['Margin'] <= 100):
        return '#ff9900'
    elif (x['Winner'] == 'GPCwins') and (x['Margin'] <= 40):
        return '#e6ffe6'
    elif (x['Winner'] == 'GPCwins') and (x['Margin'] > 40) and (x['Margin'] <= 60):
        return'#99ff99'
    elif (x['Winner'] == 'GPCwins') and (x['Margin'] > 60) and (x['Margin'] <= 80):
        return '#00e600'
    elif (x['Winner'] == 'GPCwins') and (x['Margin'] > 80) and (x['Margin'] <= 100):
        return '#009900'
    elif (x['Winner'] == 'BQwins') and (x['Margin'] <= 40):
        return '#e6faff'
    elif (x['Winner'] == 'BQwins') and (x['Margin'] > 40) and (x['Margin'] <= 60):
        return'#99ebff'
    elif (x['Winner'] == 'BQwins') and (x['Margin'] > 60) and (x['Margin'] <= 80):
        return '#4ddbff'
    elif (x['Winner'] == 'BQwins') and (x['Margin'] > 80) and (x['Margin'] <= 100):
        return '#00ccff'
    elif (x['Winner'] == 'Otherwins') and (x['Margin'] <= 40):
        return '#f2f2f2'
    elif (x['Winner'] == 'Otherwins') and (x['Margin'] > 40) and (x['Margin'] <= 60):
        return'#cccccc'
    elif (x['Winner'] == 'Otherwins') and (x['Margin'] > 60) and (x['Margin'] <= 80):
        return '#a6a6a6'
    elif (x['Winner'] == 'Otherwins') and (x['Margin'] > 80) and (x['Margin'] <= 100):
        return '#808080'
    else:
        return '#ffffff'
gdf['Fill'] = gdf.apply(colindex, axis = 1)
# Drop the Winner and Margin columns
gdf = gdf.drop(columns = ['Winner', 'Margin', 'LPCwins', 'CPCwins', 'NDPwins', 'GPCwins', 'BQwins', 'Otherwins'])

# Read in riding vote shares
probs = pd.read_csv(r"C:\Users\Donovan\Documents\Visual Studio Code\ElectionModel\SimResults\ridingvotepercentages.csv")
# Rename ridingid to FEDNUM for merge
probs = probs.rename(columns = {"districtid":"FEDNUM"})
# Merge
df = gdf.merge(probs, on='FEDNUM', how='left')
gdf = geopandas.GeoDataFrame(df)
# Capitalize Party names
gdf = gdf.rename(columns = {'lpc':'LPC', 'cpc':'CPC', 'ndp':'NDP', 'gpc':'GPC', 'bq':'BQ', 'other':'Other'})

filename = ("ridings" + str(date.today()) + ".geojson")
gdf.to_file(filename, driver='GeoJSON')
print("Geojson created")
#gdf.to_csv('test.csv', index = False)