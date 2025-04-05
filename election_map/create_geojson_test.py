import geopandas as gpd
import pandas as pd
import os 
from datetime import date

# Set working directory
os.chdir("C://projects//election_forecast")

# Load the GeoJSON file with electoral ridings
gdf = gpd.read_file('election_map//electoral_districts_2022_fed.geojson')

# Load the forecasted election results
df_election = pd.read_csv('model_results//ridingvotepercents.csv')
df_election.columns = [col.upper() for col in df_election.columns]

# Load win probabilities
df_win_probs = pd.read_csv('model_results//ridingprobabilities.csv')

# Process win probabilities data to determine winner and margin
win_columns = ['LPCwins', 'CPCwins', 'NDPwins', 'GPCwins', 'BQwins', 'PPCwins']
df_win_probs['Winner'] = df_win_probs[win_columns].idxmax(axis=1)
df_win_probs['Margin'] = df_win_probs.apply(lambda row: row[row['Winner']], axis=1)

# Create function for assigning colour based on winner and margin of victory
def func_colour_index(x):
    '''Assign color to riding based on most probable of outcome and margin of victory'''
    
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
    elif (x['Winner'] == 'PPCwins') and (x['Margin'] <= 40):
        return '#f2f2f2'
    elif (x['Winner'] == 'PPCwins') and (x['Margin'] > 40) and (x['Margin'] <= 60):
        return'#cccccc'
    elif (x['Winner'] == 'PPCwins') and (x['Margin'] > 60) and (x['Margin'] <= 80):
        return '#a6a6a6'
    elif (x['Winner'] == 'PPCwins') and (x['Margin'] > 80) and (x['Margin'] <= 100):
        return '#808080'
    else:
        return '#ffffff'

# Apply colour function
df_win_probs['Fill'] = df_win_probs.apply(func_colour_index, axis=1)

# Ensure matching datatypes for merge columns
gdf['FED_NUM'] = gdf['FED_NUM'].astype(int)
df_election['DISTRICTID'] = df_election['DISTRICTID'].astype(int)
df_win_probs['FED_NUM'] = df_win_probs['FED_NUM'].astype(int)

# Perform merges
gdf_merged = gdf.merge(
    df_election,
    left_on = 'FED_NUM',
    right_on = 'DISTRICTID',
    how = 'left'
)    

gdf_final = gdf_merged.merge(
    df_win_probs,
    on = 'FED_NUM',
    how = 'left'
)

# Save merged geojson for use in map
filename = (str(date.today())+ "_election_results_20215.geojson")
gdf_merged.to_file(filename, driver='GeoJSON')

# Success!
print("Geojson created")