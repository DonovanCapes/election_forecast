import sqlite3, csv

conn = sqlite3.connect('ridings.db')
c = conn.cursor()
c.execute("CREATE TABLE results (ridingid, LPC, CPC, NDP, GPC, BQ, Other);")

with open('ridingprobabilities.csv', 'r') as fin:
    dr = csv.DictReader(fin)
    to_db = [(i['ridingid'], i['lpc'], i['cpc'], i['ndp'], i['gpc'], i['bq'], i['other']) for i in dr]

c.executemany("INSERT INTO results (ridingid, LPC, CPC, NDP, GPC, BQ, Other) VALUES (?, ?, ?, ?, ?, ?, ?);", to_db)
conn.commit()
conn.close()
#geojson-to-sqlite ridings.db features fed_ca_2019_en.geojson --pk=FEDNUM
