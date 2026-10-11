# ETL Scanaddiction

Pipeline **extract → transform → validate → load** du catalogue.

## Lancer en local
```bash
pip install -r etl/requirements.txt
python -m etl.run                 # toutes les sources, avec quality gate
python -m etl.run --only mangadex # une seule source
python -m etl.run --no-min -v     # debug (désactive le plancher qualité)
```

## Sorties
- `data/catalogue-fr.json` — format attendu par le front (CDN fallback).
- `build/upsert.sql` — upsert D1 (séries + journal de run).
- `data/raw/<source>-<date>.raw` — couche brute (traçabilité).

## Modules
| Fichier | Rôle |
|---|---|
| `config.py` | constantes, timeouts, plancher qualité, plafonds par source |
| `http_client.py` | session `requests` durcie (retry/backoff urllib3, Retry-After, timeouts) |
| `sources.py` | un extracteur par source ; `REGISTRY` définit l'ordre/priorité |
| `models.py` | normalisation + validation (contrat de données) |
| `load.py` | écriture JSON + génération SQL (littéraux échappés) |
| `pipeline.py` | orchestration tolérante aux pannes + quality gate |
| `run.py` | CLI |

## Fiabilité des sources
Seule **MangaDex** (API officielle) est stable. Les sites protégés par Cloudflare
(Sushiscan, Raijin, Crunchyscan) peuvent renvoyer **403** depuis une IP datacenter
(runner CI) : ils sont *best-effort*, une panne n'interrompt pas le run.

> Remplace l'ancien `scraper.py` + `check_catalogue.py` (racine), désormais obsolètes.
