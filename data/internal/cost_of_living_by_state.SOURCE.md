# Source : cost_of_living_by_state.csv

**Origine** : [World Population Review — Cost of Living Index by State](https://worldpopulationreview.com/state-rankings/cost-of-living-index-by-state), qui agrège la méthodologie du **MERIC** (Missouri Economic Research and Information Center) et les **Regional Price Parities** du **BEA** (U.S. Bureau of Economic Analysis).

**Récupéré le** : 2026-07-30.

**Unité / méthodologie** : indice composite basé sur 6 sous-catégories (logement, énergie/utilities, alimentation, transport, santé, biens et services divers), normalisé de sorte que **100 = moyenne des États américains**.

- `cost_of_living_index = 185.0` (Hawaii) → le coût de la vie y est **85 % plus élevé** que la moyenne des États-Unis (un panier de biens/services qui coûte 100$ en moyenne nationale coûte environ 185$ à Hawaii).
- `cost_of_living_index = 86.0` (Oklahoma) → **14 % moins cher** que la moyenne nationale.

Ce fichier est un instantané figé (snapshot), committé dans le repo — il ne sera pas re-téléchargé automatiquement par le pipeline d'ingestion (c'est ce qui en fait une source **interne**, par opposition au Yelp Open Dataset qui est fetché en direct).
