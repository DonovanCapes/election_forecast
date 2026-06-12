import pandas as pd
import numpy as np

BASE = 'c:/GitHub/Donovan/election_forecast/model_results/'

orig = pd.read_csv(BASE + 'seatstats_original.csv')
wgt  = pd.read_csv(BASE + 'seatstats_weighted.csv')
orig.index = ['lpc','cpc','ndp','gpc','bq','ppc']
wgt.index  = ['lpc','cpc','ndp','gpc','bq','ppc']

print('=== SEAT PROJECTIONS: MEAN (original vs weighted) ===')
for party in ['lpc','cpc','ndp','gpc','bq','ppc']:
    o = orig.loc[party, 'mean']
    w = wgt.loc[party, 'mean']
    print(f'  {party.upper():<4s}  original={o:.1f}  weighted={w:.1f}  diff={w-o:+.1f}')

print()
print('=== SEAT RANGE (min / mean / max) ===')
header = f'{"Party":<6s} {"orig_min":>8s} {"orig_mean":>9s} {"orig_max":>8s}    {"wgt_min":>8s} {"wgt_mean":>9s} {"wgt_max":>8s}'
print(header)
for party in ['lpc','cpc','ndp','gpc','bq','ppc']:
    print(
        f'{party.upper():<6s}'
        f' {orig.loc[party,"min"]:>8.0f}'
        f' {orig.loc[party,"mean"]:>9.1f}'
        f' {orig.loc[party,"max"]:>8.0f}'
        f'    {wgt.loc[party,"min"]:>8.0f}'
        f' {wgt.loc[party,"mean"]:>9.1f}'
        f' {wgt.loc[party,"max"]:>8.0f}'
    )

rorig = pd.read_csv(BASE + 'ridingvotepercents_original.csv', index_col=0)
rwgt  = pd.read_csv(BASE + 'ridingvotepercents_weighted.csv', index_col=0)

parties = [p for p in ['lpc','cpc','ndp','gpc','bq'] if p in rorig.columns and p in rwgt.columns]
rdiff = rwgt[parties] - rorig[parties]

print()
print('=== BIGGEST RIDING SHIFTS (weighted vs original, top 15 by max abs change) ===')
abs_max = rdiff.abs().max(axis=1).nlargest(15)
for rid in abs_max.index:
    row = rdiff.loc[rid]
    bp = row.abs().idxmax()
    parts = '  '.join(f'{p.upper()}{row[p]:+.1f}' for p in parties)
    print(f'  FED_NUM {rid}   biggest: {bp.upper()} {row[bp]:+.1f}pp   [{parts}]')
