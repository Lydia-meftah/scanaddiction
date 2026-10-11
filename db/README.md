# Base de données (Cloudflare D1)

SQLite serverless. Schéma de référence : `db/schema.sql`. Migrations versionnées : `db/migrations/`.

## Mise en place (une fois)
```bash
npm i -g wrangler
wrangler login
wrangler d1 create scanaddiction          # → copier database_id dans wrangler.toml
wrangler d1 migrations apply scanaddiction --remote
```

## Charger les données
```bash
python -m etl.run                                         # génère build/upsert.sql
wrangler d1 execute scanaddiction --remote --file=build/upsert.sql
```
En CI, ces deux étapes tournent automatiquement si les secrets
`CLOUDFLARE_API_TOKEN` et `CLOUDFLARE_ACCOUNT_ID` sont définis dans le repo.

## Tables
- `source` — référentiel des sources (`fiable=1` = API officielle).
- `series` — catalogue (contraintes `CHECK` sur `type`/`statut`, index, `first_seen`/`last_seen`).
- `chapter` — chapitres (optionnel, pour plus tard / cache lecteur).
- `scrape_run` — journal des runs ETL (observabilité).

## Requêter
```bash
wrangler d1 execute scanaddiction --remote --command "SELECT type, COUNT(*) FROM series GROUP BY type;"
```
API de lecture publique : `GET /api/catalogue` (voir `functions/api/catalogue.js`).
