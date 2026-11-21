# %% [markdown]
# # Vitesses réelles et sécurité des cyclistes
#
# Ce notebook :
# 1. télécharge **toutes** les années disponibles des vitesses relevées par les voitures-radars à conduite externalisée (data.gouv.fr : 2021, 2023, 2024) ;
# 2. calcule, par année et par limitation, la part de véhicules au-dessus de la limite, la médiane et la V85 ;
# 3. charge les accidents corporels (BAAC 2021 à 2024) et isole les **cyclistes** (vélo et VAE) accidentés sur des voies limitées à **50 km/h ou moins** ;
# 4. croise les deux : vitesses mesurées à proximité des accidents de cyclistes, comparées aux vitesses mesurées ailleurs sur des voies ≤ 50 km/h, et analyse par carreaux de 500 m ;
# 5. produit une carte (`outputs/carte_le50.html`) et des tableaux CSV dans `outputs/`.
#
# **Exécution** : *Exécution > Tout exécuter*. Compter 10 à 20 minutes (trois fichiers de 270 à 670 Mo).
#
# **Point d'attention** : les voitures-radars circulent surtout hors agglomération. En 2021, seules 734 mesures sur 6,65 millions concernaient des tronçons à 50 km/h. Le notebook affiche le nombre de mesures ≤ 50 km/h de chaque année avant le croisement : si ce nombre est faible, les résultats du croisement ne sont pas significatifs.

# %% Paramètres
import os, re, sys, math, json
import numpy as np
import pandas as pd
import requests

LIMITE_MAX = 50      # on ne garde que les voies limitées à 50 km/h ou moins
RAYON_M = 150        # rayon autour d'un accident de cycliste pour chercher des mesures de vitesse
TAILLE_CARREAU_M = 500
CHUNK = 2_000_000

BASE = '/content' if os.path.exists('/content') else '.'
DATA = os.environ.get('VR_DATA', os.path.join(BASE, 'data'))
OUT = os.environ.get('VR_OUT', os.path.join(BASE, 'outputs'))
os.makedirs(DATA, exist_ok=True); os.makedirs(OUT, exist_ok=True)

DG = 'https://static.data.gouv.fr/resources/'
RADAR_URLS = {
    2021: DG + 'jeu-de-donnees-des-vitesses-pratiquees-issues-des-voitures-radars-a-conduite-externalisee/20221221-161623/opendata-vitesse-2021-01-01-2021-12-31.csv',
    2023: DG + 'jeux-de-donnees-des-vitesses-relevees-par-les-voitures-radars-a-conduite-externalisee/20241029-142313/opendata-vitesses-pratiquees-voitures-radars-2023-01-01-2023-12-31-.csv',
    2024: DG + 'jeux-de-donnees-des-vitesses-relevees-par-les-voitures-radars-a-conduite-externalisee/20260113-144502/opendata-vitesses-pratiquees-voitures-radars-2024-01-01-2024-12-31.csv',
}
B = DG + 'bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-'
BAAC_URLS = {
    2021: {'caract': B + '2020/20221024-113743/carcteristiques-2021.csv', 'lieux': B + '2020/20221024-113901/lieux-2021.csv',
           'vehicules': B + '2020/20221024-113925/vehicules-2021.csv', 'usagers': B + '2022/20231009-140337/usagers-2021.csv'},
    2022: {'caract': B + '2021/20231005-093927/carcteristiques-2022.csv', 'lieux': B + '2021/20231005-094112/lieux-2022.csv',
           'vehicules': B + '2021/20231005-094147/vehicules-2022.csv', 'usagers': B + '2021/20231005-094229/usagers-2022.csv'},
    2023: {'caract': B + '2023/20241028-103125/caract-2023.csv', 'lieux': B + '2023/20241023-153219/lieux-2023.csv',
           'vehicules': B + '2023/20241023-153253/vehicules-2023.csv', 'usagers': B + '2023/20241023-153328/usagers-2023.csv'},
    2024: {'caract': B + '2024/20251021-115900/caract-2024.csv', 'lieux': B + '2024/20251021-115812/lieux-2024.csv',
           'vehicules': B + '2024/20251107-100240/vehicules-2024.csv', 'usagers': B + '2024/20251021-115506/usagers-2024.csv'},
}

def fmt(n):
    return f'{int(n):,}'.replace(',', '\u202f')

def telecharger(url, nom):
    """Télécharge une fois, en flux, dans DATA."""
    chemin = os.path.join(DATA, nom)
    if os.path.exists(chemin) and os.path.getsize(chemin) > 0:
        return chemin
    print('Téléchargement', nom, '...', flush=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(chemin + '.part', 'wb') as f:
            for bloc in r.iter_content(1 << 22):
                f.write(bloc)
    os.replace(chemin + '.part', chemin)
    return chemin

# %% [markdown]
# ## 1. Vitesses relevées par les voitures-radars
# Les fichiers sont lus par blocs de 2 millions de lignes. Pour chaque année on garde :
# - la distribution complète (limite × vitesse mesurée), pour les statistiques ;
# - toutes les mesures sur voies ≤ 50 km/h, avec leur position, pour le croisement.

# %%
def separateur(ligne):
    return ';' if ligne.count(';') >= 1 else ('\t' if ligne.count('\t') >= 1 else ',')

def colonnes(cols):
    m = {}
    for c in cols:
        l = c.lower().strip().strip('"')
        if 'limit' in l or l == 'vma':
            m[c] = 'limite'
        elif 'mesure' in l or 'vitesse' in l:
            m[c] = 'mesure'
        elif 'date' in l or 'heure' in l:
            m.setdefault(c, 'date')
        elif 'position' in l or 'geo' in l or 'coord' in l:
            m[c] = 'position'
        elif l in ('lat', 'latitude', 'y'):
            m[c] = 'lat'
        elif l in ('lon', 'lng', 'long', 'longitude', 'x'):
            m[c] = 'lon'
    return m

NUM = r'(-?\d+(?:\.\d+)?)'
def latlon(df):
    if 'lat' not in df.columns:
        p = df['position'].astype(str).str.extract(NUM + r'\s*[,; ]\s*' + NUM)
        df['lat'] = pd.to_numeric(p[0], errors='coerce'); df['lon'] = pd.to_numeric(p[1], errors='coerce')
    else:
        for c in ('lat', 'lon'):
            df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')
    # au cas où l'ordre serait lon, lat
    if df['lat'].median() < 20 and df['lon'].median() > 35:
        df[['lat', 'lon']] = df[['lon', 'lat']].values
    return df

def lire_radar(annee, chemin):
    with open(chemin, encoding='utf-8', errors='replace') as f:
        entete = f.readline()
    sep = separateur(entete)
    hist, basses, n = {}, [], 0
    for bloc in pd.read_csv(chemin, sep=sep, chunksize=CHUNK, dtype=str, encoding='utf-8', encoding_errors='replace'):
        if n == 0:
            print(f'{annee} : colonnes {list(bloc.columns)}')
            print(bloc.head(3).to_string(), '\n')
        bloc = bloc.rename(columns=colonnes(bloc.columns))
        bloc['mesure'] = pd.to_numeric(bloc['mesure'], errors='coerce')
        bloc['limite'] = pd.to_numeric(bloc['limite'], errors='coerce')
        bloc = bloc.dropna(subset=['mesure', 'limite'])
        n += len(bloc)
        for (lim, v), k in bloc.groupby(['limite', 'mesure']).size().items():
            hist[(int(lim), int(v))] = hist.get((int(lim), int(v)), 0) + int(k)
        b = bloc[bloc['limite'] <= LIMITE_MAX].copy()
        if len(b):
            b = latlon(b)
            garder = [c for c in ('date', 'lat', 'lon', 'mesure', 'limite') if c in b.columns]
            basses.append(b[garder])
    h = pd.Series(hist, name='n'); h.index.names = ['limite', 'mesure']
    h = h.reset_index(); h['annee'] = annee
    basses = pd.concat(basses) if basses else pd.DataFrame(columns=['date', 'lat', 'lon', 'mesure', 'limite'])
    basses['annee'] = annee
    print(f'{annee} : {fmt(n)} mesures lues, dont {fmt(len(basses))} sur voies ≤ {LIMITE_MAX} km/h')
    return h, basses

HIST, BASSES = [], []
for annee, url in RADAR_URLS.items():
    chemin = telecharger(url, f'radar_{annee}.csv')
    h, b = lire_radar(annee, chemin)
    HIST.append(h); BASSES.append(b)
HIST = pd.concat(HIST, ignore_index=True)
RADAR50 = pd.concat(BASSES, ignore_index=True).dropna(subset=['lat', 'lon'])
HIST.to_csv(os.path.join(OUT, 'distribution_vitesses.csv'), index=False)
RADAR50.to_csv(os.path.join(OUT, 'mesures_le50.csv'), index=False)

# %% [markdown]
# ## 2. Statistiques des excès par année et par limitation
# - **> limite** : mesure brute au-dessus de la limitation ;
# - **> limite + 5 / + 10** : au-delà de la marge technique (5 km/h sous 100 km/h pour les radars fixes, 10 km/h pour les radars mobiles embarqués) ;
# - **≥ limite + 20** et **≥ limite + 50** (seuil du délit) ;
# - **V85** : vitesse sous laquelle roulent 85 % des véhicules.

# %%
def stats(g):
    lim = g.name[1]; n = g['n'].sum()
    g = g.sort_values('mesure'); cum = g['n'].cumsum() / n
    q = lambda p: int(g.loc[cum >= p, 'mesure'].iloc[0])
    part = lambda cond: g.loc[cond, 'n'].sum() / n * 100
    return pd.Series({'mesures': n, 'mediane': q(.5), 'V85': q(.85),
                      '% > limite': part(g['mesure'] > lim), '% > limite+5': part(g['mesure'] > lim + 5),
                      '% > limite+10': part(g['mesure'] > lim + 10), '% ≥ limite+20': part(g['mesure'] >= lim + 20),
                      '% ≥ limite+50': part(g['mesure'] >= lim + 50)})

STATS = HIST.groupby(['annee', 'limite'])[['mesure', 'n']].apply(stats).reset_index()
STATS['mesures'] = STATS['mesures'].astype(int)
STATS.to_csv(os.path.join(OUT, 'stats_exces_par_annee.csv'), index=False)
pd.set_option('display.float_format', '{:.2f}'.format)
display(STATS) if 'display' in globals() else print(STATS.to_string())

# %%
import matplotlib
if not os.path.exists('/content'):
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
lims = sorted(HIST['limite'].unique())
fig, axes = plt.subplots(1, len(lims), figsize=(4 * len(lims), 3.2), sharey=False)
axes = np.atleast_1d(axes)
for ax, lim in zip(axes, lims):
    for annee, g in HIST[HIST['limite'] == lim].groupby('annee'):
        g = g.sort_values('mesure'); ax.plot(g['mesure'], g['n'] / g['n'].sum() * 100, label=str(annee))
    ax.axvline(lim, color='#d22630', ls='--'); ax.set_title(f'Limite {lim} km/h'); ax.set_xlabel('km/h')
axes[0].set_ylabel('% des mesures'); axes[0].legend()
plt.tight_layout(); plt.savefig(os.path.join(OUT, 'distributions.png'), dpi=130); plt.show()

# %% [markdown]
# ## 3. Cyclistes accidentés sur voies limitées à 50 km/h ou moins (BAAC 2021-2024)
# Un cycliste = usager d'un véhicule de catégorie 1 (bicyclette) ou 80 (vélo à assistance électrique).
# La limitation est celle du lieu de l'accident (`vma`, fichier *lieux*). Gravité : 1 indemne, 2 tué, 3 hospitalisé, 4 blessé léger.

# %%
def lire_baac(chemin):
    for enc in ('utf-8', 'latin-1'):
        try:
            with open(chemin, encoding=enc) as f:
                sep = separateur(f.readline())
            df = pd.read_csv(chemin, sep=sep, dtype=str, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    df.columns = [c.strip().strip('"').replace('﻿', '') for c in df.columns]
    df = df.rename(columns={'Accident_Id': 'Num_Acc'})
    return df.apply(lambda s: s.str.strip().str.strip('"') if s.dtype == object else s)

def nombre(s):
    return pd.to_numeric(s.astype(str).str.replace(',', '.'), errors='coerce')

CYCL = []
for annee, fichiers in BAAC_URLS.items():
    t = {k: lire_baac(telecharger(u, f'baac_{k}_{annee}.csv')) for k, u in fichiers.items()}
    car, lie, veh, usa = t['caract'], t['lieux'], t['vehicules'], t['usagers']
    car['lat'] = nombre(car['lat']); car['lon'] = nombre(car['long'])
    lie['vma'] = nombre(lie['vma'])
    lie = lie.drop_duplicates('Num_Acc')          # un lieu par accident (le premier)
    cle = ['Num_Acc', 'id_vehicule'] if 'id_vehicule' in usa.columns and 'id_vehicule' in veh.columns else ['Num_Acc', 'num_veh']
    u = usa.merge(veh[cle + ['catv', 'manv'] + (['num_veh'] if 'num_veh' not in cle else [])], on=cle, how='left', suffixes=('', '_v'))
    velo = u[u['catv'].isin(['1', '80'])].copy()
    # véhicule antagoniste : premier autre véhicule de l'accident
    autres = veh[~veh['catv'].isin(['1', '80'])].drop_duplicates('Num_Acc')[['Num_Acc', 'catv', 'manv']]
    autres.columns = ['Num_Acc', 'catv_autre', 'manv_autre']
    velo = velo.merge(autres, on='Num_Acc', how='left')
    velo = velo.merge(car[['Num_Acc', 'lat', 'lon', 'agg', 'col', 'lum']], on='Num_Acc', how='left')
    velo = velo.merge(lie[['Num_Acc', 'vma', 'catr']], on='Num_Acc', how='left')
    velo['annee'] = annee
    velo['grav'] = pd.to_numeric(velo['grav'], errors='coerce')
    CYCL.append(velo[['Num_Acc', 'annee', 'lat', 'lon', 'agg', 'catr', 'vma', 'col', 'lum', 'grav', 'catv', 'manv', 'catv_autre', 'manv_autre']])
    print(f'{annee} : {fmt(len(velo))} cyclistes impliqués')
CYCL = pd.concat(CYCL, ignore_index=True)
C50 = CYCL[(CYCL['vma'] > 0) & (CYCL['vma'] <= LIMITE_MAX)].dropna(subset=['lat', 'lon']).copy()
C50 = C50[C50['lat'].between(41, 52) & C50['lon'].between(-5.5, 10)]   # métropole
C50.to_csv(os.path.join(OUT, 'cyclistes_le50.csv'), index=False)

LIB_GRAV = {1: 'indemne', 2: 'tué', 3: 'hospitalisé', 4: 'blessé léger'}
LIB_COL = {'1': 'frontale', '2': "par l'arrière", '3': 'par le côté', '4': 'en chaîne', '5': 'multiples', '6': 'autre', '7': 'sans collision'}
LIB_MANV = {'1': 'sans changement de direction', '2': 'même sens, même file', '15': 'tourne à gauche', '16': 'tourne à droite',
            '17': 'dépasse à gauche', '18': 'dépasse à droite', '9': "s'insère", '22': 'ouverture de portière', '13': 'déporté à gauche', '14': 'déporté à droite'}
print('\nCyclistes victimes sur voies ≤ 50 km/h, par année et gravité')
print(pd.crosstab(C50['annee'], C50['grav'].map(LIB_GRAV), margins=True).to_string())
print('\nPar limitation du lieu')
print(pd.crosstab(C50['vma'], C50['grav'].map(LIB_GRAV), margins=True).to_string())
print('\nType de collision (cyclistes tués ou hospitalisés)')
ksi = C50[C50['grav'].isin([2, 3])]
print(ksi['col'].map(LIB_COL).value_counts(normalize=True).mul(100).round(1).to_string())
print("\nManœuvre de l'autre véhicule (cyclistes tués ou hospitalisés)")
print(ksi['manv_autre'].map(LIB_MANV).fillna('autre / aucun').value_counts(normalize=True).mul(100).round(1).head(10).to_string())

# %% [markdown]
# ## 4. Croisement : vitesses mesurées près des accidents de cyclistes
# Deux approches complémentaires, toutes deux limitées aux voies ≤ 50 km/h :
# 1. **Proximité** : chaque mesure de vitesse est classée « près d'un accident de cycliste » si un cycliste a été blessé ou tué à moins de `RAYON_M` mètres. On compare les deux groupes.
# 2. **Carreaux** de 500 m : part d'excès dans le carreau contre nombre de cyclistes victimes dans le carreau (corrélation de rang de Spearman).
#
# Limite : on ne connaît pas le trafic cycliste (l'exposition). Un lien statistique n'est pas une preuve de causalité.

# %%
from sklearn.neighbors import BallTree
from scipy.stats import spearmanr, mannwhitneyu
R_TERRE = 6_371_000

print(f'Mesures de vitesse sur voies ≤ {LIMITE_MAX} km/h : {fmt(len(RADAR50))}')
print(RADAR50.groupby(['annee', 'limite']).size().to_string())
VICT = C50[C50['grav'].isin([2, 3, 4])]
print(f'Cyclistes victimes sur voies ≤ {LIMITE_MAX} km/h : {fmt(len(VICT))}')
if len(RADAR50) < 5000:
    print('\n⚠️  Très peu de mesures sur voies ≤ 50 km/h : les voitures-radars circulent surtout hors agglomération. '
          'Les résultats ci-dessous sont indicatifs et ne doivent pas être généralisés.')

PRES = pd.DataFrame()
if len(RADAR50) and len(VICT):
    arbre = BallTree(np.radians(VICT[['lat', 'lon']].values), metric='haversine')
    nb = arbre.query_radius(np.radians(RADAR50[['lat', 'lon']].values), r=RAYON_M / R_TERRE, count_only=True)
    RADAR50['pres_accident'] = nb > 0
    RADAR50['exces'] = RADAR50['mesure'] > RADAR50['limite']
    RADAR50['exces10'] = RADAR50['mesure'] > RADAR50['limite'] + 10
    RADAR50['ecart'] = RADAR50['mesure'] - RADAR50['limite']
    PRES = RADAR50.groupby('pres_accident').agg(mesures=('mesure', 'size'), ecart_median=('ecart', 'median'),
        V85_ecart=('ecart', lambda s: s.quantile(.85)), pct_exces=('exces', 'mean'), pct_exces10=('exces10', 'mean'))
    PRES[['pct_exces', 'pct_exces10']] *= 100
    PRES.index = PRES.index.map({True: f'à moins de {RAYON_M} m d\'un accident vélo', False: 'ailleurs'})
    print('\n', PRES.round(2).to_string())
    a = RADAR50.loc[RADAR50['pres_accident'], 'ecart']; b = RADAR50.loc[~RADAR50['pres_accident'], 'ecart']
    if len(a) > 20 and len(b) > 20:
        print('\nTest de Mann-Whitney (écart à la limite, près vs ailleurs) : p =', f"{mannwhitneyu(a, b, alternative='greater').pvalue:.4f}")
    PRES.to_csv(os.path.join(OUT, 'croisement_proximite.csv'))

# %%
def carreau(df):
    lat0 = 46.5
    y = (df['lat'] * 111_320 // TAILLE_CARREAU_M).astype(int)
    x = (df['lon'] * 111_320 * math.cos(math.radians(lat0)) // TAILLE_CARREAU_M).astype(int)
    return x.astype(str) + '_' + y.astype(str)

CARR = pd.DataFrame()
if len(RADAR50) and len(VICT):
    RADAR50['carreau'] = carreau(RADAR50); VICT = VICT.assign(carreau=carreau(VICT))
    CARR = RADAR50.groupby('carreau').agg(mesures=('mesure', 'size'), lat=('lat', 'mean'), lon=('lon', 'mean'),
                                          pct_exces=('exces', 'mean'), pct_exces10=('exces10', 'mean'),
                                          V85=('mesure', lambda s: s.quantile(.85)))
    v = VICT.groupby('carreau').agg(victimes=('grav', 'size'), tues_hosp=('grav', lambda s: s.isin([2, 3]).sum()))
    CARR = CARR.join(v, how='left').fillna({'victimes': 0, 'tues_hosp': 0})
    CARR = CARR[CARR['mesures'] >= 30]
    print(f'Carreaux de {TAILLE_CARREAU_M} m avec au moins 30 mesures : {len(CARR)}')
    if len(CARR) >= 10:
        rho, p = spearmanr(CARR['pct_exces'], CARR['victimes'])
        print(f'Spearman part d\'excès ~ cyclistes victimes : rho = {rho:.2f} (p = {p:.3f})')
        CARR['classe'] = pd.qcut(CARR['pct_exces'].rank(method='first'), 3, labels=['excès faible', 'moyen', 'fort'])
        print(CARR.groupby('classe', observed=True).agg(carreaux=('mesures', 'size'), pct_exces=('pct_exces', lambda s: s.mean() * 100),
              victimes_par_carreau=('victimes', 'mean'), part_avec_victime=('victimes', lambda s: (s > 0).mean())).to_string())
    CARR.to_csv(os.path.join(OUT, 'croisement_carreaux.csv'))

# %% [markdown]
# ## 5. Carte
# Cercles rouges : carreaux de 500 m mesurés sur voies ≤ 50 km/h (couleur = part d'excès). Points bleus : cyclistes tués ou hospitalisés sur voies ≤ 50 km/h.

# %%
import folium
from folium.plugins import MarkerCluster
centre = [RADAR50['lat'].mean(), RADAR50['lon'].mean()] if len(RADAR50) else [46.6, 2.4]
carte = folium.Map(location=centre, zoom_start=7, tiles='cartodbpositron')
def couleur(p):
    return '#f6d3d5' if p < .1 else '#ee8f95' if p < .25 else '#d22630' if p < .5 else '#7d1118'
for _, c in CARR.iterrows():
    folium.CircleMarker([c['lat'], c['lon']], radius=4 + min(c['mesures'], 2000) ** .4, color=couleur(c['pct_exces']), fill=True,
        fill_opacity=.8, weight=0, tooltip=f"{int(c['mesures'])} mesures · {c['pct_exces']*100:.0f} % > limite · V85 {c['V85']:.0f} km/h · {int(c['victimes'])} cycliste(s) victime(s)").add_to(carte)
grappe = MarkerCluster(name='Cyclistes tués ou hospitalisés').add_to(carte)
for _, a in C50[C50['grav'].isin([2, 3])].iterrows():
    folium.CircleMarker([a['lat'], a['lon']], radius=3, color='#1f5fbf' if a['grav'] == 3 else '#000', fill=True,
        tooltip=f"{int(a['annee'])} · {LIB_GRAV.get(a['grav'])} · VMA {a['vma']:.0f}").add_to(grappe)
folium.LayerControl().add_to(carte)
carte.save(os.path.join(OUT, 'carte_le50.html'))
carte

# %% [markdown]
# ## 6. Récapitulatif et téléchargement
# Les fichiers produits sont dans `outputs/`. Dans Colab, la cellule suivante les zippe et les télécharge.

# %%
print(STATS[STATS['limite'] <= LIMITE_MAX].to_string())
if os.path.exists('/content'):
    import shutil
    shutil.make_archive('/content/resultats_vitesses', 'zip', OUT)
    from google.colab import files
    files.download('/content/resultats_vitesses.zip')
