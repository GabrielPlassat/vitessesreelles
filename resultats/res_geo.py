import pandas as pd, numpy as np, reverse_geocoder as rg, sys, json
Z=sys.argv[1]
m=pd.read_csv(f'{Z}/mesures_le50.csv'); m=m[m.annee==2024]
r=rg.search(list(zip(m.lat,m.lon)),mode=1)
m['ville']=[x['name'] for x in r]; m['dep']=[x['admin2'] for x in r]; m['reg']=[x['admin1'] for x in r]; m['cc']=[x['cc'] for x in r]
m=m[m.cc=='FR']
m['gt']=m.mesure>50; m['gt60']=m.mesure>60; m['ge70']=m.mesure>=70
D=m.groupby('dep').agg(n=('mesure','size'),gt=('gt','mean'),gt60=('gt60','mean'),ge70=('ge70','mean'),v85=('mesure',lambda s:s.quantile(.85))).sort_values('n',ascending=False)
print(D.head(30).round(3).to_string())
R=m.groupby('reg').agg(n=('mesure','size'),gt=('gt','mean'),gt60=('gt60','mean'),ge70=('ge70','mean')).sort_values('n',ascending=False); print(R.round(3).to_string())
V=m.groupby(['ville','dep']).agg(n=('mesure','size'),gt=('gt','mean'),gt60=('gt60','mean'),ge70=('ge70','mean'),v85=('mesure',lambda s:s.quantile(.85)),lat=('lat','mean'),lon=('lon','mean')).reset_index()
V=V[V.n>=300].sort_values('ge70',ascending=False); print(len(V)); print(V.head(25).round(3).to_string())
# hours
m['h']=pd.to_datetime(m.date).dt.hour
print(m.groupby('h').agg(n=('mesure','size'),gt60=('gt60','mean')).round(3).T.to_string())
m.to_pickle('/home/claude/res/m2024.pkl')
