import pandas as pd, numpy as np, reverse_geocoder as rg, json, sys, re
Z=sys.argv[1]
C=pd.read_csv(f'{Z}/exces_par_carreau.csv')
C=C[C.lat.between(41.3,51.2)&C.lon.between(-5.3,9.7)]
R=C[C.limite.isin([70,80,90])]
# totals per year/limit from cells (check)
print(R.groupby(['annee','limite'])[['n','n_gt','n_ge20']].sum().assign(p=lambda d:d.n_gt/d.n*100,p20=lambda d:d.n_ge20/d.n*100).round(2))
# common cells evolution
k=['limite','cx','cy']
piv=R[R.n>=100].pivot_table(index=k,columns='annee',values=['n','n_gt','n_ge20'],aggfunc='sum')
com=piv.dropna()
print('cellules communes',len(com))
evo={}
for l,g in com.groupby(level='limite'):
    row={}
    for y in [2021,2023,2024]:
        row[y]=[int(g[('n',y)].sum()),round(g[('n_gt',y)].sum()/g[('n',y)].sum()*100,1),round(g[('n_ge20',y)].sum()/g[('n',y)].sum()*100,2)]
    evo[int(l)]=dict(cells=len(g),**{str(y):v for y,v in row.items()}); print(l,len(g),row)
# also 2023->2024 common (more cells)
p2=R[R.n>=100].pivot_table(index=k,columns='annee',values=['n','n_gt'],aggfunc='sum')
c2=p2[[('n',2023),('n',2024)]].dropna().index
g=p2.loc[c2]
evo2={}
for l,gg in g.groupby(level='limite'):
    a=gg[('n_gt',2023)].sum()/gg[('n',2023)].sum()*100; b=gg[('n_gt',2024)].sum()/gg[('n',2024)].sum()*100
    evo2[int(l)]=[len(gg),round(a,1),round(b,1)]; print('23-24',l,len(gg),round(a,1),round(b,1))
# 2024 department ranking
D=R[R.annee==2024].copy()
r=rg.search(list(zip(D.lat,D.lon)),mode=1)
D['dep']=[x['admin2'] for x in r]; D['cc']=[x['cc'] for x in r]; D=D[D.cc=='FR']
D['dep']=D.dep.str.replace(r"^Departement (du |de la |de l'|des |de |d')",'',regex=True)
dep={}
for l in [80,90,70]:
    s=D[D.limite==l].groupby('dep')[['n','n_gt','n_gt10','n_ge20']].sum()
    s=s[s.n>=(20000 if l==80 else 10000 if l==90 else 5000)]
    s['p']=s.n_gt/s.n*100; s['p10']=s.n_gt10/s.n*100; s['p20']=s.n_ge20/s.n*100
    s=s.sort_values('p20',ascending=False)
    print(l,len(s)); print(s.head(12).round(1).to_string()); print(s.tail(5).round(1).to_string())
    dep[l]=[[i,int(r_.n),round(r_.p,1),round(r_.p10,1),round(r_.p20,2)] for i,r_ in s.iterrows()]
# map 2024: 10 km aggregation for 80 roads (and 90)
mp={}
for l in [80,90]:
    s=R[(R.annee==2024)&(R.limite==l)].copy()
    s['X']=s.cx//5; s['Y']=s.cy//5
    a=s.groupby(['X','Y']).agg(n=('n','sum'),gt=('n_gt','sum'),ge20=('n_ge20','sum'),slat=('lat',lambda v:(v*s.loc[v.index,'n']).sum()),slon=('lon',lambda v:(v*s.loc[v.index,'n']).sum())).reset_index()
    a=a[a.n>=300]; a['lat']=a.slat/a.n; a['lon']=a.slon/a.n
    mp[l]=[[round(r_.lat,3),round(r_.lon,3),int(r_.n),round(r_.gt/r_.n*100,1),round(r_.ge20/r_.n*100,1)] for r_ in a.itertuples()]
    print('map',l,len(mp[l]), np.percentile([m[4] for m in mp[l]],[25,50,75,90]))
# top hotspots 10km for 80 with n>=2000 by ge20
s=R[(R.annee==2024)&(R.limite==80)].copy(); s['X']=s.cx//5; s['Y']=s.cy//5
a=s.groupby(['X','Y']).agg(n=('n','sum'),gt=('n_gt','sum'),ge20=('n_ge20','sum'),lat=('lat','mean'),lon=('lon','mean')).reset_index()
a=a[a['n']>=2000]; a['p20']=a['ge20']/a['n']*100; a['p']=a['gt']/a['n']*100; a=a.sort_values('p20',ascending=False).head(15)
rr=rg.search(list(zip(a.lat,a.lon)),mode=1); a['ville']=[x['name'] for x in rr]; a['dep']=[re.sub(r"^Departement (du |de la |de l'|des |de |d')",'',x['admin2']) for x in rr]
print(a.round(2).to_string())
hot=[[v,d,int(n),round(p,1),round(q,1)] for v,d,n,p,q in zip(a.ville,a.dep,a['n'],a.p,a.p20)]
json.dump({'evo':evo,'evo2':evo2,'dep':dep,'map':mp,'hot':hot},open('page3.json','w'),separators=(',',':'),ensure_ascii=False)
import os; print(os.path.getsize('page3.json'))
