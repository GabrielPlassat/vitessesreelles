import pandas as pd, numpy as np, json, sys
from scipy.stats import spearmanr
Z=sys.argv[1]
c=pd.read_csv(f'{Z}/cyclistes_le50.csv',dtype={'col':str,'manv_autre':str,'catv_autre':str})
v=c[c.grav.isin([2,3,4])]
print('victimes',len(v), v.grav.value_counts().to_dict())
print('par an', v.groupby(['annee','grav']).size().unstack().to_dict('index'))
for vma in [30,50]:
    s=v[v.vma==vma]; print('vma',vma,len(s),'tués',(s.grav==2).sum(),'let',round((s.grav==2).mean()*100,2),'ksi',round(s.grav.isin([2,3]).mean()*100,1))
s=v[v.vma<30]; print('vma<30',len(s),(s.grav==2).sum())
k=v[v.grav.isin([2,3])]; t=v[v.grav==2]
LIB_COL={'1':'frontale','2':"par l'arrière",'3':'par le côté','4':'en chaîne','5':'multiples','6':'autre','7':'sans collision'}
print('col ksi', k.col.map(LIB_COL).value_counts(normalize=True).round(3).to_dict())
print('col tués', t.col.map(LIB_COL).value_counts(normalize=True).round(3).to_dict())
print('catv autre ksi', k.catv_autre.value_counts(normalize=True).head(8).round(3).to_dict())
print('catv autre tués', t.catv_autre.value_counts(normalize=True).head(8).round(3).to_dict())
print('manv autre ksi', k.manv_autre.value_counts(normalize=True).head(10).round(3).to_dict())
# lethality by other vehicle
for cv,lab in [('7','VL'),('2','x'),('10','VU'),('13','PL'),('14','PL'),('15','PL'),('33','moto'),('0','aucun')]:
    s=v[v.catv_autre==cv]; 
    if len(s): print('autre',cv,lab,len(s),round((s.grav==2).mean()*100,2))
s=v[v.catv_autre.isna()]; print('aucun autre',len(s),round((s.grav==2).mean()*100,2))
# carreaux
cc=pd.read_csv(f'{Z}/croisement_carreaux.csv')
print('carreaux',len(cc), 'avec victime',(cc.victimes>0).sum())
print('spearman exc~vict',spearmanr(cc.pct_exces,cc.victimes))
print('spearman V85~vict',spearmanr(cc.V85,cc.victimes))
print('spearman exc10~ksi',spearmanr(cc.pct_exces10,cc.tues_hosp))
cc['cl']=pd.qcut(cc.pct_exces.rank(method='first'),3,labels=['faible','moyen','fort'])
print(cc.groupby('cl',observed=True).agg(n=('mesures','size'),exc=('pct_exces','mean'),V85=('V85','median'),vict=('victimes','mean'),avec=('victimes',lambda s:(s>0).mean()),ksi=('tues_hosp','mean')))
