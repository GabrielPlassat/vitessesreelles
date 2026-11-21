# Vitesses réelles et sécurité des cyclistes

Analyse des vitesses relevées par les voitures-radars à conduite externalisée (données ouvertes du ministère de l'Intérieur), croisées avec les accidents corporels de cyclistes (BAAC).

[![Ouvrir dans Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/GabrielPlassat/vitessesreelles/blob/main/analyse_vitesses_cyclistes.ipynb)

## Le notebook `analyse_vitesses_cyclistes.ipynb`

À lancer dans Google Colab (*Exécution > Tout exécuter*, 10 à 20 minutes). Il :

1. télécharge toutes les années de vitesses publiées sur data.gouv.fr (2021, 2023, 2024 : 270 à 670 Mo chacune) et les lit par blocs ;
2. calcule par année et par limitation : médiane, V85, part au-dessus de la limite, au-delà de la marge technique, à +20 km/h et à +50 km/h (délit) ;
3. charge le BAAC 2021-2024 et garde les **cyclistes (vélo et VAE) accidentés sur des voies limitées à 50 km/h ou moins** (`vma` du lieu) ;
4. croise les deux sur les voies ≤ 50 km/h :
   - vitesses mesurées à moins de 150 m d'un accident de cycliste, comparées aux vitesses mesurées ailleurs (test de Mann-Whitney) ;
   - carreaux de 500 m : part d'excès contre nombre de cyclistes victimes (corrélation de Spearman) ;
5. produit une carte interactive et des CSV dans `outputs/`, puis les télécharge en zip.

Paramètres modifiables en tête de notebook : `LIMITE_MAX` (50), `RAYON_M` (150), `TAILLE_CARREAU_M` (500).

Le fichier `analyse_vitesses_cyclistes.py` est la même chose en script Python.

### À savoir avant de lire les résultats

- **Les voitures-radars circulent surtout hors agglomération.** En 2021, 734 mesures sur 6,65 millions concernaient des tronçons à 50 km/h, avec une vitesse médiane d'environ 95 km/h, ce qui évoque des erreurs de lecture de panneau plutôt que de la circulation urbaine. Le notebook affiche le nombre de mesures ≤ 50 km/h de chaque année et prévient si l'échantillon est trop faible.
- Les mesures sont brutes, avant déduction de la marge technique.
- On ne connaît pas le trafic cycliste par lieu : un lien statistique entre excès et accidents n'est pas une preuve de causalité, et une absence de lien n'est pas une preuve d'innocuité.
- Le BAAC n'enregistre pas la vitesse des véhicules impliqués.

## Première analyse 2021 (`docs/index.html`, `analyse_2021_koumoul/`)

Faite à partir des agrégations de l'API Koumoul (année 2021 uniquement). Principaux résultats :

| Limite | Mesures | Médiane | V85 | > limite | > limite + 10 | ≥ limite + 20 |
|---|---:|---:|---:|---:|---:|---:|
| 70 km/h | 166 404 | 67 | 78 | 37,2 % | 11,4 % | 3,1 % |
| 80 km/h | 4 690 965 | 74 | 86 | 30,2 % | 8,8 % | 2,8 % |
| 90 km/h | 1 715 656 | 82 | 93 | 22,6 % | 5,6 % | 1,9 % |

- Dans l'Ouest, les grands excès (≥ 100 km/h sur route à 80) se concentrent entre Châteaubriant, Segré et La Guerche-de-Bretagne, et à l'est de Laval (jusqu'à 8,5 % des mesures).
- Cyclistes victimes 2019-2024 : 12 % sont tués hors agglomération contre 2 % en agglomération ; un quart des cyclistes tués hors agglomération l'ont été dans une collision par l'arrière.
- À l'échelle de grandes zones, aucune corrélation positive n'apparaît entre taux d'excès et létalité des accidents de vélo (biais d'exposition et de couverture).

`docs/index.html` est la page de synthèse ; elle peut être publiée avec GitHub Pages (dossier `docs/`).

## Sources

- [Vitesses relevées par les voitures-radars à conduite externalisée](https://www.data.gouv.fr/datasets/jeux-de-donnees-des-vitesses-relevees-par-les-voitures-radars-a-conduite-externalisee), ministère de l'Intérieur, data.gouv.fr
- [Bases de données annuelles des accidents corporels de la circulation routière (BAAC)](https://www.data.gouv.fr/datasets/bases-de-donnees-annuelles-des-accidents-corporels-de-la-circulation-routiere-annees-de-2005-a-2025), ministère de l'Intérieur, data.gouv.fr
- [Koumoul : vitesses pratiquées](https://opendata.koumoul.com/datasets/vitesses-pratiquees-issues-des-voitures-radars-a-conduite-externalisee) et [accidents de vélo](https://opendata.koumoul.com/datasets/accidents-velos)
- ONISR, bilans de l'accidentalité routière 2023 et 2024
