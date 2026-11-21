# Cellule à coller à la fin du notebook (après « Tout exécuter »).
# Relit les fichiers de vitesses déjà téléchargés dans data/ et calcule, pour chaque carreau de 2 km,
# année et limitation : nombre de mesures, part au-dessus de la limite, à +10 et à +20 km/h, vitesse moyenne.
# Résultat : outputs/exces_par_carreau.csv, puis un nouveau zip téléchargé.
import os, math, glob, shutil
import numpy as np, pandas as pd

TAILLE_KM = 2
BASE = '/content' if os.path.exists('/content') else '.'
DATA = os.environ.get('VR_DATA', os.path.join(BASE, 'data'))
OUT = os.environ.get('VR_OUT', os.path.join(BASE, 'outputs'))
os.makedirs(OUT, exist_ok=True)

def _colonnes(cols):
    m = {}
    for c in cols:
        l = c.lower().strip().strip('"')
        if 'limit' in l or l == 'vma': m[c] = 'limite'
        elif 'mesure' in l or 'vitesse' in l: m[c] = 'mesure'
        elif 'position' in l or 'geo' in l or 'coord' in l: m[c] = 'position'
        elif l in ('lat', 'latitude', 'y'): m[c] = 'lat'
        elif l in ('lon', 'lng', 'long', 'longitude', 'x'): m[c] = 'lon'
    return m

_NUM = r'(-?\d+(?:\.\d+)?)'
agg = []
for chemin in sorted(glob.glob(os.path.join(DATA, 'radar_*.csv'))):
    annee = int(os.path.basename(chemin)[6:10])
    with open(chemin, encoding='utf-8', errors='replace') as f:
        entete = f.readline()
    sep = ';' if ';' in entete else ('\t' if '\t' in entete else ',')
    for bloc in pd.read_csv(chemin, sep=sep, chunksize=2_000_000, dtype=str, encoding_errors='replace'):
        bloc = bloc.rename(columns=_colonnes(bloc.columns))
        if 'lat' not in bloc.columns:
            p = bloc['position'].astype(str).str.extract(_NUM + r'\s*[,; ]\s*' + _NUM)
            bloc['lat'], bloc['lon'] = p[0], p[1]
        d = pd.DataFrame({'lat': pd.to_numeric(bloc['lat'].astype(str).str.replace(',', '.'), errors='coerce'),
                          'lon': pd.to_numeric(bloc['lon'].astype(str).str.replace(',', '.'), errors='coerce'),
                          'mesure': pd.to_numeric(bloc['mesure'], errors='coerce'),
                          'limite': pd.to_numeric(bloc['limite'], errors='coerce')}).dropna()
        if d['lat'].median() < 20 and d['lon'].median() > 35:
            d[['lat', 'lon']] = d[['lon', 'lat']].values
        pas = TAILLE_KM * 1000
        d['cy'] = (d['lat'] * 111_320 // pas).astype(int)
        d['cx'] = (d['lon'] * 111_320 * math.cos(math.radians(46.5)) // pas).astype(int)
        d['gt'] = d['mesure'] > d['limite']
        d['gt10'] = d['mesure'] > d['limite'] + 10
        d['ge20'] = d['mesure'] >= d['limite'] + 20
        g = d.groupby(['cx', 'cy', 'limite']).agg(n=('mesure', 'size'), somme=('mesure', 'sum'), n_gt=('gt', 'sum'),
                                                   n_gt10=('gt10', 'sum'), n_ge20=('ge20', 'sum'),
                                                   slat=('lat', 'sum'), slon=('lon', 'sum')).reset_index()
        g['annee'] = annee
        agg.append(g)
    print(annee, 'traité', flush=True)

C = pd.concat(agg).groupby(['annee', 'limite', 'cx', 'cy'], as_index=False).sum()
C['lat'] = (C['slat'] / C['n']).round(5); C['lon'] = (C['slon'] / C['n']).round(5)
C['vitesse_moy'] = (C['somme'] / C['n']).round(1)
for k in ('gt', 'gt10', 'ge20'):
    C['pct_' + k] = (C['n_' + k] / C['n'] * 100).round(2)
C = C.drop(columns=['somme', 'slat', 'slon'])
C['limite'] = C['limite'].astype(int)
C.to_csv(os.path.join(OUT, 'exces_par_carreau.csv'), index=False)
print(len(C), 'lignes écrites dans exces_par_carreau.csv')
print(C.groupby(['annee', 'limite'])['n'].agg(['size', 'sum']).rename(columns={'size': 'carreaux', 'sum': 'mesures'}).to_string())

if os.path.exists('/content'):
    shutil.make_archive('/content/resultats_vitesses', 'zip', OUT)
    from google.colab import files
    files.download('/content/resultats_vitesses.zip')
