# Scanaddiction

Plateforme communautaire de scantrad amateur francophone. Des manga et manhwa traduits avec passion, loin des gros sites répétitifs.

**Site en ligne : <https://scanaddiction.pages.dev>**

## Fonctionnalités

- Catalogue des séries (FR) avec recherche et filtres
- Lecteur intégré multi-sources (Cloudflare Pages Functions, `functions/api`)
- Page œuvre avec détails et liste des chapitres
- Suggestions de lecture
- Pages soutien, contact, à propos et mentions légales
- SEO : `sitemap.xml`, `robots.txt`, redirections (`_redirects`) et en-têtes de sécurité (`_headers`)
- Tracking GA4 + GTM (`js/tracking.js`) : events catalogue, lecteur, scroll

## Stack technique

- Site statique : HTML / CSS / JavaScript vanilla
- Hébergement : Cloudflare Pages (+ Pages Functions pour l'API du lecteur)
- Données : fichiers JSON dans `data/`, alimentés par `scraper.py` (AniList + MangaDex)
- CI : GitHub Actions (`.github/workflows`)
- Analytics : Google Analytics 4 + Google Tag Manager

## Structure du projet

```
.
├── index.html            # Accueil
├── catalogue.html        # Catalogue des séries
├── oeuvre.html           # Fiche d'une série
├── lecteur.html          # Lecteur de chapitres
├── suggestions.html      # Suggestions de lecture
├── css/                  # Styles
├── js/                   # Scripts (app, catalogue, lecteur, oeuvre, tracking…)
├── data/                 # Données JSON des séries
├── functions/api/        # Cloudflare Pages Functions (proxy lecteur)
├── scraper.py            # Mise à jour du catalogue
└── sitemap.xml
```

## Développement local

```bash
# Servir le site en local
npx wrangler pages dev .
```

Le déploiement est automatique : chaque push sur `main` déclenche un build Cloudflare Pages.
