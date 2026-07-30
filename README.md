# Yelp Data Lake & Warehouse

Plateforme data lake / data warehouse en architecture **Medallion** (Bronze → Silver → Gold) construite sur le dataset Yelp Open Dataset. Ingestion de données structurées et non-structurées (5 Go+), transformations Spark automatisées avec validation qualité, KPIs métier exposés en base, et monitoring des opérations par couche via Prometheus/Grafana.

## Architecture

```
Sources externes (API, scraping, téléchargements)
                │
                ▼
        ┌───────────────┐
        │  Bronze layer │  données brutes, format d'origine préservé
        └───────┬───────┘
                │  Spark (validation, dédup, typage)
                ▼
        ┌───────────────┐
        │  Silver layer │  données nettoyées, indexées
        └───────┬───────┘
                │  Spark (agrégations, KPIs)
                ▼
        ┌───────────────┐
        │   Gold layer  │  data warehouse (PostgreSQL)
        └───────────────┘
```

- **Stockage (Bronze/Silver/Gold)** : MinIO (S3-compatible), choisi plutôt que HDFS pour rester conteneurisé sur le réseau Docker du projet, sans dépendance cloud externe. Justification détaillée dans le rapport.
- **Traitement** : Apache Spark en cluster (1 master + 2 workers), non local.
- **Data warehouse** : PostgreSQL pour les KPIs de la couche Gold.
- **Monitoring** : Prometheus (métriques) + Grafana (dashboards) + Node Exporter (ressources hôte) + Postgres Exporter (opérations DB).

## Prérequis

- Docker + Docker Compose v2
- ~10 Go d'espace disque libre (images + données + volumes)

## Démarrage

Toute la configuration passe par `.env` (aucune étape manuelle) :

```bash
docker compose up -d
docker compose ps
```

Pour arrêter :

```bash
docker compose down
```

## Services & URLs

| Service | URL | Identifiants |
|---|---|---|
| Spark Master UI | http://localhost:8080 | — |
| MinIO Console | http://localhost:9001 | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` (voir `.env`) |
| MinIO API (S3) | http://localhost:9000 | idem |
| Grafana | http://localhost:3000 | `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` (voir `.env`) |
| Prometheus | http://localhost:9090 | — |
| PostgreSQL | localhost:5432 | `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` (voir `.env`) |
| Node Exporter | http://localhost:9100/metrics | — |

Les ports par défaut sont modifiables dans `.env`.

## Structure du projet

```
.
├── docker-compose.yml          # Définition des services (Spark, MinIO, Postgres, monitoring)
├── .env                        # Configuration (credentials, ports, ressources Spark)
├── conf/                       # Configuration Spark montée dans le cluster
├── data/                       # Données locales (sorties, échantillons)
├── jobs/                       # Jobs Spark (ingestion Bronze, transformation Silver/Gold)
└── monitoring/
    ├── prometheus.yml          # Scrape config Prometheus
    └── grafana/provisioning/   # Datasources Grafana auto-provisionnées
```

## Statut

- [x] Infrastructure Docker Compose (Spark, MinIO, PostgreSQL, monitoring)
- [ ] Scripts d'ingestion Bronze (sources internes + externes)
- [ ] Jobs Spark Silver (validation, déduplication, qualité)
- [ ] Jobs Spark Gold (KPIs, agrégations)
- [ ] Dashboards Grafana (ressources + opérations par couche)
- [ ] Makefile d'orchestration
