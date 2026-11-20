# L'équipe IA de Scanaddiction

Une équipe de 8 agents spécialisés, coordonnée par un agent CTO. Elle tourne à deux endroits :

- **dans Claude Code** (session interactive) : commande `/equipe <objectif>` ;
- **sur GitHub Actions** (en continu) : tickets étiquetés `agent:<rôle>`, relecture des PR, audit hebdomadaire.

## Organigramme

```
                    Propriétaire du dépôt (fusionne sur main)
                                   │
                          ┌────────┴────────┐
                          │   CTO / manager  │  découpe, assigne, tranche, relit, approuve
                          └────────┬────────┘
   ┌──────────┬──────────┬────────┼─────────┬──────────┬──────────┐
 dev-       dev-       data-     securite   seo-perf     qa       ml-ocr
 frontend   backend    engineer
```

## Postes et périmètres

| Agent | Poste | Fichiers dont il est responsable |
|---|---|---|
| `cto` | Coordination, arbitrage, relecture et approbation des PR | `CLAUDE.md`, `docs/equipe/` |
| `dev-frontend` | Pages, interface, accessibilité, Tailwind | `*.html`, `css/`, `js/` |
| `dev-backend` | Pages Functions, API, cache, en-têtes HTTP | `functions/`, `_headers`, `_redirects` |
| `data-engineer` | Scraper, catalogue, schémas JSON, workflow nocturne | `scraper.py`, `check_catalogue.py`, `data/`, `scans/index.json`, `.github/workflows/scrape.yml` |
| `securite` | CSP, secrets, permissions CI, dépendances, revue sécurité | `_headers` (CSP, avec dev-backend), permissions dans `.github/workflows/` |
| `seo-perf` | Référencement, métadonnées, performance, Core Web Vitals | `sitemap.xml`, `robots.txt`, balises `<head>` (avec dev-frontend) |
| `qa` | Contrôles, tests, non-régression, CI | `scripts/`, `tests/`, `.github/workflows/qualite.yml` |
| `ml-ocr` | Chaîne OCR + traduction + lettrage (contenus sous droits uniquement) | `outils/ocr/` |

## Cycle de travail

1. **Cadrage** : le CTO lit l'objectif, `CLAUDE.md`, `DECISIONS.md`, les tickets et PR ouverts.
2. **Découpage** : tickets avec un responsable, des fichiers précis et des critères d'acceptation.
   Deux tickets lancés en parallèle ne modifient jamais les mêmes fichiers.
3. **Exécution en parallèle** : chaque agent travaille sur sa branche `agent/<rôle>/<sujet>` et lance
   `bash scripts/qualite.sh`.
4. **Relecture CTO** : grille de `.claude/agents/cto.md`. Au plus 2 allers-retours, sinon le CTO tranche.
5. **PR** : le CTO pose `cto:approuvé` ou `cto:changements` avec ses remarques.
6. **Fusion** : par la propriétaire du dépôt.
7. **Traçabilité** : toute décision structurante va dans `DECISIONS.md`.

## Déclencher l'équipe sur GitHub

| Je veux… | Je fais… |
|---|---|
| Confier un ticket à un agent | Créer un ticket et lui mettre le label `agent:dev-frontend` (ou un autre rôle) |
| Poser une question ou demander une retouche | Commenter `@claude …` dans un ticket ou une PR |
| Faire relire ma propre PR par le CTO | Automatique à l'ouverture de la PR |
| Lancer un audit complet | Actions → « 🧭 Audit hebdo » → Run workflow (sinon automatique le lundi) |

Prérequis : voir la section « Mise en route » du README.
