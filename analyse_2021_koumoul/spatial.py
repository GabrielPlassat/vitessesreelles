import json
from data_raw import *
B32='0123456789bcdefghjkmnpqrstuvwxyz'
def decode(g):
    lat=[-90,90]; lon=[-180,180]; even=True
    for c in g:
        v=B32.index(c)
        for m in (16,8,4,2,1):
            r=lon if even else lat; mid=(r[0]+r[1])/2
            if v&m: r[0]=mid
            else: r[1]=mid
            even=not even
    return lat,lon
def P(s):
    out={}
    for p in s.replace('\n',' ').replace(',',' ').split():
        k,v=p.split('|'); out[k]=int(v)
    return out
t,e,g=P(G3_TOT),P(G3_EXC),P(G3_GE); aa,at,ak=P(A3_ALL),P(A3_TUE),P(A3_KSI)
rows=[]
for c in t:
    if t[c]<40000: continue
    la,lo=decode(c)
    rows.append(dict(c=c,lat=(la[0]+la[1])/2,lon=(lo[0]+lo[1])/2,n=t[c],exc=e.get(c,0)/t[c],ge=g.get(c,0)/t[c],
        acc=aa.get(c,0),tues=at.get(c,0),ksi=ak.get(c,0),let=at.get(c,0)/aa[c] if aa.get(c) else None))
def rank(x):
    s=sorted(range(len(x)),key=lambda i:x[i]); r=[0]*len(x)
    for j,i in enumerate(s): r[i]=j
    return r
def spearman(a,b):
    ra,rb=rank(a),rank(b); n=len(a); ma=sum(ra)/n; mb=sum(rb)/n
    cov=sum((x-ma)*(y-mb) for x,y in zip(ra,rb)); va=sum((x-ma)**2 for x in ra); vb=sum((y-mb)**2 for y in rb)
    return cov/(va*vb)**.5
R=[r for r in rows if r['acc']>=30]
print(len(rows),len(R))
for r in sorted(R,key=lambda r:-r['exc']): print(r['c'],round(r['lat'],1),round(r['lon'],1),r['n'],round(r['exc']*100,1),round(r['ge']*100,2),r['acc'],r['tues'],round(r['let']*100,1))
print('spearman exc~let',round(spearman([r['exc'] for r in R],[r['let'] for r in R]),2))
print('spearman ge~let',round(spearman([r['ge'] for r in R],[r['let'] for r in R]),2))
# terciles
R2=sorted(R,key=lambda r:r['exc']); k=len(R2)//3
for name,grp in [('bas',R2[:k]),('moyen',R2[k:2*k]),('haut',R2[2*k:])]:
    A=sum(r['acc'] for r in grp); T=sum(r['tues'] for r in grp); K=sum(r['ksi'] for r in grp)
    print(name,round(min(r['exc'] for r in grp)*100,1),round(max(r['exc'] for r in grp)*100,1),A,T,round(T/A*100,1),round(K/A*100,1))
# gh4 ouest
t4,e4,g4,a4=P(G4_TOT),P(G4_EXC),P(G4_GE),P(A4_KSI)
cells=[]
for c in t4:
    la,lo=decode(c)
    cells.append(dict(c=c,s=la[0],n_=la[1],w=lo[0],e=lo[1],n=t4[c],exc=e4.get(c,0)/t4[c],ge=g4.get(c,0)/t4[c],ksi=a4.get(c,0)))
for c in a4:
    if c not in t4:
        la,lo=decode(c); cells.append(dict(c=c,s=la[0],n_=la[1],w=lo[0],e=lo[1],n=0,exc=None,ge=None,ksi=a4[c]))
C=[c for c in cells if c['n']>=5000]
print('gh4 cells',len(C),'spearman ge~ksi',round(spearman([c['ge'] for c in C],[c['ksi'] for c in C]),2),'exc~ksi',round(spearman([c['exc'] for c in C],[c['ksi'] for c in C]),2))
top=sorted(C,key=lambda c:-c['ge'])[:12]
for c in top: print('top',c['c'],round((c['s']+c['n_'])/2,2),round((c['w']+c['e'])/2,2),c['n'],round(c['exc']*100,1),round(c['ge']*100,2),c['ksi'])
json.dump({'g3':rows,'g4':cells},open('spatial.json','w'))
