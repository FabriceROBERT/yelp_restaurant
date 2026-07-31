-- ============================================================
-- Schéma Gold - Data Warehouse PostgreSQL
-- Exécuté automatiquement au premier démarrage du conteneur Postgres
-- (docker-entrypoint-initdb.d), cf. docker-compose.yml.
--
-- Scope actuel : A1, A3, A4 (dashboard gérant/analyste). A2 (météo) et les
-- fonctionnalités B1-B4 (recommandation) sont volontairement absentes tant
-- qu'elles ne sont pas implémentées - la table sera ajoutée avec le job qui
-- la peuple pour ne pas laisser de schéma mort.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS gold;

-- ------------------------------------------------------------
-- Dimension : coût de la vie par état (source interne, snapshot figé)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.dim_cost_of_living (
    state_code              CHAR(2) PRIMARY KEY,
    state_name              VARCHAR(100) NOT NULL,
    cost_of_living_index    NUMERIC(6,2) NOT NULL
);

-- ------------------------------------------------------------
-- A1 : note moyenne et volume d'avis par catégorie / ville / prix
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.kpi_business (
    id                  SERIAL PRIMARY KEY,
    categorie           VARCHAR(100),
    ville               VARCHAR(100),
    state_code          CHAR(2),
    gamme_prix          VARCHAR(10),
    note_moyenne        NUMERIC(3,2),
    nb_avis_total       INTEGER,
    nb_etablissements   INTEGER,
    date_calcul         TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- A2 : corrélation météo <-> fréquentation (checkins)
-- Limité aux villes couvertes par l'ingestion météo (échantillon des villes
-- les plus représentées, cf. jobs/ingest_bronze_weather.py - le quota
-- horaire gratuit d'Open-Meteo ne permet pas de couvrir toutes les villes).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.kpi_meteo_frequentation (
    id                      SERIAL PRIMARY KEY,
    ville                   VARCHAR(100),
    condition_meteo         VARCHAR(50),   -- 'pluie' | 'beau_temps'
    nb_checkins_moyen_jour  NUMERIC(10,2),
    date_calcul             TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- A3 : coût de la vie vs positionnement prix / note, par état
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.kpi_cout_vie_prix (
    id                          SERIAL PRIMARY KEY,
    state_code                  CHAR(2),  -- pas de FK stricte : le job Gold TRUNCATE/recharge
                                           -- dim_cost_of_living et kpi_cout_vie_prix indépendamment
                                           -- à chaque exécution (ETL batch, cohérence assurée par le job)
    cost_of_living_index        NUMERIC(6,2),
    gamme_prix_moyenne          NUMERIC(3,2),
    note_moyenne_etat           NUMERIC(3,2),
    nb_etablissements           INTEGER,
    date_calcul                 TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- A4 : score de valeur perçue par établissement
-- (note ajustée par le prix normalisé au coût de la vie local)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gold.score_valeur_percue (
    id                      SERIAL PRIMARY KEY,
    business_id             VARCHAR(50),
    nom                     VARCHAR(255),
    state_code              CHAR(2),
    ville                   VARCHAR(100),
    gamme_prix              VARCHAR(10),
    note_moyenne            NUMERIC(3,2),
    cost_of_living_index    NUMERIC(6,2),
    score_valeur_ajuste     NUMERIC(6,4),
    date_calcul             TIMESTAMP DEFAULT NOW()
);

-- ------------------------------------------------------------
-- Index
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_kpi_business_ville ON gold.kpi_business(ville);
CREATE INDEX IF NOT EXISTS idx_kpi_business_categorie ON gold.kpi_business(categorie);
CREATE INDEX IF NOT EXISTS idx_cout_vie_state ON gold.kpi_cout_vie_prix(state_code);
CREATE INDEX IF NOT EXISTS idx_score_valeur_business ON gold.score_valeur_percue(business_id);
