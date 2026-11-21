import json, math
from data_raw import *
def parse(s, sep=','):
    out={}
    for p in s.replace('\n',' ').split(sep if sep!=' ' else None):
        p=p.strip()
        if not p: continue
        k,v=p.split(':') if ':' in p else p.split('|'); out[k]=int(v)
    return out
def dist(s): return {int(k):v for k,v in parse(s).items()}
res={}
for lim,s in [(70,D70),(80,D80),(90,D90)]:
    d=dist(s); n=sum(d.values())
    def share(f): return sum(v for k,v in d.items() if f(k))/n
    xs=sorted(d); cum=0; p50=p85=None
    for k in xs:
        cum+=d[k]
        if p50 is None and cum>=n*.5: p50=k
        if p85 is None and cum>=n*.85: p85=k
    mean=sum(k*v for k,v in d.items())/n
    # parmi véhicules en circulation "libre" : >= limite-20
    free={k:v for k,v in d.items() if k>=lim-20}; nf=sum(free.values())
    res[lim]=dict(n=n,count=COUNTS[lim],gt=share(lambda k:k>lim),verb=share(lambda k:k>lim+10),
      ge20=share(lambda k:k>=lim+20),ge30=share(lambda k:k>=lim+30),ge50=share(lambda k:k>=lim+50),
      n_gt=sum(v for k,v in d.items() if k>lim), n_ge20=sum(v for k,v in d.items() if k>=lim+20), n_ge50=sum(v for k,v in d.items() if k>=lim+50),
      p50=p50,p85=p85,mean=mean,max=max(xs),
      gt_free=sum(v for k,v in free.items() if k>lim)/nf, nfree=nf)
for k,v in res.items(): print(k,{a:(round(b,4) if isinstance(b,float) else b) for a,b in v.items()})
# histo 80 bins of 5 for chart
d=dist(D80); h={}
for k,v in d.items():
    b=min(5*(k//5),160); h[b]=h.get(b,0)+v
print(sorted(h.items()))
json.dump({'stats':res,'hist80':sorted(h.items()),'hist90':sorted({b:sum(v for k,v in dist(D90).items() if min(5*(k//5),160)==b) for b in range(20,165,5)}.items())},open('stats.json','w'))
