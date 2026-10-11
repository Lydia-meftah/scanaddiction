# Fiche technique — Scanaddiction

> Toutes les spécifications techniques du projet, en un seul document.
> Complément du `CAHIER-DES-CHARGES.md`. Version 1.0 — 2026-10-11.

---

## 1. Stack technique

| Couche | Technologie |
|--------|-------------|
| **Front-end** | HTML statique + Tailwind CSS (CDN `cdn.tailwindcss.com`) + CSS custom (`css/style.css`) |
| **JavaScript** | Vanilla JS (aucun framework), modules par page dans `js/` |
| **Données** | Fichier JSON statique `data/catalogue-fr.json` |
| **Back-end / API** | Cloudflare Pages Function (serverless) `functions/api/chapter.js` |
| **Scraping** | Python 3.12 (`scraper.py`), unique dépendance : `requests` |
| **CI/CD** | GitHub Actions (`.github/workflows/scrape.yml`) |
| **Hébergement** | Cloudflare Pages (CDN mondial, HTTPS, déploiement auto) |
| **Analytics** | Google Analytics 4 + Google Tag Manager |
| **Automatisation** | Make (scénario de notification Discord) |
| **Outillage MCP** | `.mcp.json` : serveurs GitHub + Make |

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub (repo scanaddiction)                │
│  code front + scraper.py + data/catalogue-fr.json            │
│                                                               │
│  GitHub Actions (cron 3h UTC) ── scraper.py ──► MangaDex API  │
│        │                                   └──► Sitemaps XML  │
│        │                                        (4 sites)     │
│        └── commit data/catalogue-fr.json                      │
└───────────────┬───────────────────────────────────────────────┘
                │ push main
                ▼
┌─────────────────────────────────────────────────────────────┐
│                      Cloudflare Pages                         │
│  Sert les pages statiques + /data/*.json                     │
│  Function /api/chapter  ──(proxy, whitelist)──► sites Madara │
│  _headers (CSP, cache)   _redirects (alias 301)              │
└───────────────┬───────────────────────────────────────────────┘
                │ HTTPS
                ▼
         Navigateur du lecteur
   ├─ Mode A : lecteur-fr.html?id=  ─────► api.mangadex.org (direct)
   └─ Mode B : lecteur-fr.html?src= ─────► /api/chapter (proxy CF)
```

## 3. Environnements & URLs

| Élément | Valeur |
|---------|--------|
| Production | `https://scanaddiction-pages.pages.dev` |
| Dépôt Git | `github.com/Lydia-meftah/scanaddiction` |
| Branche prod | `main` (push → déploiement auto ~1-2 min) |
| Proxy API | `/api/chapter` |
| Données | `/data/catalogue-fr.json` |

## 4. Modèle de données — `data/catalogue-fr.json`

### Enveloppe
```json
{
  "lastUpdate": "2026-06-13T00:00:00Z",   // ISO 8601 UTC
  "total": 0,                              // nombre d'œuvres
  "sources": [],                           // liste des sources présentes
  "oeuvres": []                            // tableau d'œuvres (voir ci-dessous)
}
```

### Objet « œuvre »
```json
{
  "id": "mdx-<uuid>",            // préfixé par source : mdx- cs- sm- ss- rj-
  "mangadexId": "<uuid>",        // présent si source MangaDex (lecteur mode A)
  "titre": "…",
  "url": "https://…",            // page source de l'œuvre
  "cover": "https://…",          // URL de couverture (peut être vide)
  "type": "manga|manhwa|manhua",
  "statut": "en cours|terminé|pause|annulé",
  "synopsis": "…",
  "genres": ["action", "…"],
  "auteur": "…",
  "note": 0.0,
  "dernierChapitre": 0,
  "sourceNom": "MangaDex|Crunchyscan|Scan-Manga|Sushiscan|Raijin",
  "sourceUrl": "https://…",
  "lecteurIntegre": true          // true = lisible sur le site
}
```
> Déduplication des œuvres par `id`, tri alphabétique sur le titre (insensible à la casse).

## 5. Scraper — `scraper.py`

- **Config** : `HTTP_TIMEOUT = 30 s`, `DELAY = 1.2 s` entre requêtes, User-Agent dédié `Scanaddiction/1.0`.
- **Sortie** : `data/catalogue-fr.json`.
- **Tolérance aux pannes** : chaque source est encapsulée ; une source en échec est loggée (`stderr`) sans interrompre les autres.
- **Sources** :

| Source | Méthode d'acquisition | Type dominant |
|--------|----------------------|---------------|
| **MangaDex** | API REST officielle `api.mangadex.org` (traductions FR), 100/page, max offset 500 | manga / manhwa |
| **Crunchyscan** | Sitemaps XML (`manga-sitemap.xml`, Yoast) | manhwa |
| **Scan-Manga** | Page « En cours » + meta OG (SSR) | manga/manhwa |
| **Sushiscan** | `wp-sitemap-posts-manga-1..3.xml` (bypass Cloudflare via sitemaps) | manga |
| **Raijin-Scans** | Sitemaps chapitres → extraction + dédup des slugs `/manga/{slug}/` | manhwa |

- **Mapping statuts MangaDex** : `ongoing→en cours`, `completed→terminé`, `hiatus→pause`, `cancelled→annulé`.
- **Vérification** : `check_catalogue.py` valide le JSON généré avant commit.

## 6. CI/CD — `.github/workflows/scrape.yml`

- **Déclencheurs** : `cron: '0 3 * * *'` (3h00 UTC, chaque nuit) + `workflow_dispatch` (bouton manuel).
- **Runner** : `ubuntu-latest`, timeout 45 min, Python 3.12, `pip install requests`.
- **Étapes** : checkout → setup Python → scraper.py → `check_catalogue.py` → commit & push de `data/catalogue-fr.json` **uniquement s'il y a un diff**.
- **Permissions** : `contents: write`. Commit par `github-actions[bot]`.

## 7. API interne — `functions/api/chapter.js` (Cloudflare Pages Function)

Proxy serverless qui contourne CORS et extrait images/chapitres des sites Madara.

| Endpoint | Paramètres | Réponse |
|----------|-----------|---------|
| `GET /api/chapter` | `?url={page_chapitre}&mode=chapter` | `{ images: [...], count, source }` |
| `GET /api/chapter` | `?url={page_série}&mode=chapters` | `{ chapters: [...], count, source }` |

- **CORS** : gère `OPTIONS` (préflight).
- **Whitelist de domaines** (`ALLOWED`) : `sushiscan.net`, `raijin-scans.fr`, `crunchyscan.fr`, `scan-manga.com`. Hors whitelist → **403**. `www.` normalisé, sous-domaines acceptés.
- **Validation** : `?url=` obligatoire, URL parsable, sinon erreur.
- **4 méthodes d'extraction images** (dans l'ordre) : `ts_reader.run({sources:[{images}]})` → `chapter_preloaded_images` (JSON embarqué) → attribut `data-src` → attribut `src`. Filtrage des `placeholder`, `logo`, `icon`.
- **Extraction chapitres** : parse la liste, numéro + titre (tronqué 80 car.), tri croissant par numéro.
- **Objet chapitre** : `{ url, num, title }`.

## 8. Sécurité

### 8.1 Headers HTTP — `_headers` (appliqués par Cloudflare Pages)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()`
- **CSP** :
  - `default-src 'self'`
  - `script-src 'self' 'unsafe-inline' cdn.tailwindcss.com googletagmanager.com google-analytics.com`
  - `style-src 'self' 'unsafe-inline' cdn.tailwindcss.com fonts.googleapis.com`
  - `font-src 'self' fonts.gstatic.com`
  - `img-src 'self' data: https: blob:`
  - `connect-src 'self' api.mangadex.org google-analytics.com googletagmanager.com fonts.googleapis.com`
  - `frame-ancestors 'none'`
- **Cache** : `/*` → `max-age=3600` ; `/data/*` → `max-age=300` ; `/api/*` → `no-store` + `X-Robots-Tag: noindex`.

### 8.2 Protections Cloudflare — à activer manuellement (dashboard)
- **Rate limiting** : `/api/chapter*` → 30 req/min/IP (block 1 h) ; `/*` → 300 req/min/IP (block 10 min).
- **Bot Fight Mode** : ON.
- **WAF** : Cloudflare Managed Rules → ON.
- **DDoS** : HTTP DDoS Attack Protection → High.

## 9. Routage & redirections — `_redirects`
- `/manga` → `/catalogue.html` (301)
- `/lire` → `/catalogue.html` (301)
- 404 servie automatiquement par `404.html`.

## 10. Analytics — `js/tracking.js`
- Chargé sur toutes les pages, pousse 12 événements personnalisés (détail §5.7 du cahier des charges).
- **À configurer** : `GTM_ID` (ligne ~35) et `GA4_ID` (ligne ~36) — actuellement placeholders.

## 11. Secrets & configuration à renseigner

| Variable / secret | Où | Statut |
|-------------------|-----|--------|
| `GTM-XXXXXXX` (container GTM) | `js/tracking.js` | 🔴 placeholder |
| `G-XXXXXXXXXX` (propriété GA4) | `js/tracking.js` | 🔴 placeholder |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | `.mcp.json` | 🔴 `REMPLACE_PAR_TON_TOKEN` |
| Token Make (Bearer) | `.mcp.json` | 🔴 `REMPLACE_PAR_TON_TOKEN_MAKE` |
| Email masqué GitHub (noreply) | GitHub Settings → Emails | 🔴 à activer |

> ⚠️ Ne jamais committer de token réel. `.mcp.json` devrait être couvert par `.gitignore` ou utiliser des secrets GitHub/CF.

## 12. Dette technique & TODO connus

1. **Catalogue vide** — `catalogue-fr.json` actuellement `total: 0` (dernier run utile non concluant). → Fiabiliser le scraper et vérifier le run GitHub Actions.
2. **IDs analytics placeholder** — créer container GTM + propriété GA4, injecter les IDs.
3. **Protections Cloudflare non activées** — rate limiting, Bot Fight, WAF, DDoS (§8.2).
4. **Anonymisation email** — activer email masqué + blocage des push exposant l'email.
5. **Tokens dans `.mcp.json`** — déplacer vers des secrets, sortir du versionnement.
6. **RGPD / consentement** — pas de bandeau cookies alors que GA4/GTM sont injectés.
7. **Deux catalogues** — `catalogue.html` (ancien) vs `catalogue-fr.html` (généré) + `data/oeuvres.json` (démo) vs `data/catalogue-fr.json` (prod) : clarifier/supprimer le legacy.

## 13. Conventions & organisation du dépôt

```
scan project/
├─ index.html, catalogue(-fr).html, lecteur(-fr).html, oeuvre.html,
│  suggestions.html, apropos.html, contact.html, soutien.html,
│  mentions-legales.html, 404.html
├─ css/style.css
├─ js/  app.js · catalogue.js · lecteur.js · oeuvre.js · suggestions.js · tracking.js
├─ data/  catalogue-fr.json (prod) · oeuvres.json (démo legacy)
├─ functions/api/chapter.js        # Cloudflare Pages Function
├─ scraper.py · check_catalogue.py
├─ .github/workflows/scrape.yml
├─ _headers · _redirects · robots.txt · sitemap.xml
├─ make-scenario-discord.json · .mcp.json
└─ docs/  CAHIER-DES-CHARGES.md · SPECS-TECHNIQUES.md
```
- **Branche `main` = production** : tout push déclenche un déploiement. Préférer des branches de travail + PR pour les changements risqués.

---

## 14. Nouvelle base de données & ETL (v2 — construite le 2026-10-11)

Refonte de la couche données : d'un script → JSON plat vers une **base relationnelle D1 + ETL structuré**, le tout testé contre SQLite (schéma, contraintes, upsert idempotent, FK/CHECK vérifiés).

### 14.1 Base de données (Cloudflare D1 / SQLite)
- `db/schema.sql` — source de vérité ; tables `source`, `series`, `chapter`, `scrape_run`.
- `db/migrations/` — `0001_init.sql`, `0002_seed_sources.sql` (wrangler d1 migrations).
- `wrangler.toml` — binding `DB` + `migrations_dir`.
- Garanties : `CHECK` sur `type`/`statut`, clés étrangères, index (source/type/statut/titre), `first_seen`/`last_seen` (détection des séries disparues), journal `scrape_run`.

### 14.2 ETL (`etl/`)
Pipeline **extract → transform → validate → load**, tolérant aux pannes, avec quality gate (plancher 50) et filet de sécurité (ne jamais écraser un bon catalogue par du vide).
- `http_client.py` — session `requests` durcie : retry/backoff urllib3 (429/5xx), respect de `Retry-After`, timeouts connect/read séparés. Réf. [peterbe — retries with requests](https://www.peterbe.com/plog/best-practice-with-retries-with-requests).
- `sources.py` — un extracteur par source ; MangaDex = seule source fiable (API officielle), les sites Cloudflare sont best-effort.
- `load.py` — écrit `data/catalogue-fr.json` (compat front) + `build/upsert.sql` (littéraux SQL échappés, upsert `ON CONFLICT`).
- Sorties traçables : couche brute `data/raw/`.

### 14.3 API lecture sur D1
- `functions/api/catalogue.js` — `GET /api/catalogue?type=&statut=&source=&q=&limit=&offset=` en **requêtes préparées `.bind()`** (pas d'injection), filtres validés par enum.

### 14.4 Durcissement sécurité du proxy
`functions/api/chapter.js` réécrit selon l'[OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) :
- `https://` imposé, pas d'identifiants dans l'URL, port standard, allowlist d'hôtes exacte ;
- **redirections non suivies** (`redirect:'manual'`) — corrige la classe SSRF « SSRF via redirect following » ;
- délai max (AbortController 15 s) + plafond de réponse (5 Mo) ;
- CORS restreint aux origines du site (réduit l'usage en proxy ouvert).

### 14.5 Secrets & CI
- `.mcp.json` et `.dev.vars` sortis du versionnement (`.gitignore`) ; fournis en `.example`. **À faire : `git rm --cached .mcp.json`** (déjà tracké).
- Workflow `scrape.yml` refondu : `python -m etl.run` → (si secrets CF) `wrangler d1 migrations apply` + `execute build/upsert.sql` → commit JSON → alerte Discord sur échec.
- Secrets CI à créer : `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `DISCORD_WEBHOOK` (optionnel).

### 14.6 Références consultées (GitHub / SO / docs)
- [D1 best practices & migrations (Cloudflare)](https://developers.cloudflare.com/d1/reference/migrations/) · [wrangler commands](https://developers.cloudflare.com/d1/reference/wrangler-commands)
- [urllib3 Retry + HTTPAdapter (peterbe)](https://www.peterbe.com/plog/best-practice-with-retries-with-requests) · [architecting resilient scrapers with HTTP adapters (dev.to)](https://dev.to/appcyberyozh/stop-using-timesleep-architecting-resilient-python-scrapers-with-http-adapters-8do)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

---

## 15. Traducteur Scanaddiction (outil local) & mode de lecture « Scanaddiction »

> Ajouté le 2026-10-11. Dossier `traducteur/` (exclu du site public via `_redirects`).

| Élément | Détail |
|---------|--------|
| **Appli** | FastAPI sur `127.0.0.1:7860` uniquement + mot de passe (`APP_PASSWORD`, cookie HMAC). Lancement `lancer.bat`, installation `installer.bat` (Python 3.12, PyTorch CUDA cu128). |
| **Pipeline** | EasyOCR/CRAFT (détection, webtoons découpés en tuiles 1600 px) → **Claude vision** (page annotée, bulles numérotées, glossaire + 25 dernières répliques de la série ; renvoie texte relu, type, traduction FR) → **LaMa** (effacement uniquement des bulles retenues, par fenêtres) → lettrage Pillow (Comic Neue, détection de l'intérieur de bulle par flood-fill, contour auto). Sortie WebP q90, bandes > 8000 px découpées hors bulles. |
| **Cohérence** | Glossaire par série `work/glossaires/<slug>.json` (termes, notes de style, contexte), enrichi automatiquement par Claude, éditable dans l'appli. |
| **Correction** | Édition bulle par bulle + re-lettrage local (sans rappel API). |
| **Agent** | Lien(s) de chapitre → extraction images (ts_reader, chapter_preloaded_images, data-src/src, MangaDex API) → identification série/chapitre/langue par Claude (rattachement aux séries existantes) → traduction → publication. Aussi `agent.py` / `agent-lien.bat`. |
| **Config** | `traducteur/.env` (non versionné) : `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` (défaut `claude-sonnet-5-5`), `TRADUIRE_SFX`, `R2_*`, `SITE_URL`. |

### Stockage R2 (bucket `scanaddiction-scans`)
```
index.json                      catalogue des séries hébergées (format œuvre + champ "serie", sourceNom "Scanaddiction")
<slug>/series.json              { slug, titre, type, statut, synopsis, genres, auteur, cover, chapitres:[{num, titre, date, pages:[...]}] }
<slug>/cover.webp
<slug>/<chapitre>/<NNN>.webp    cache immutable 1 an
```

### Côté site
- **Function** `functions/scans/[[path]].js` : sert `/scans/*` depuis le binding R2 **`SCANS`** (lecture seule, chemins filtrés, ETag/304, JSON 120 s). Binding déclaré dans `wrangler.toml` + à créer dans Pages → Settings → Bindings.
- **Lecteur** `lecteur-fr.html` : **mode C** `?serie=<slug>&chapter=<n°>` (prioritaire sur `?id=` et `?src=`).
- **Catalogue** `catalogue-fr.html` : fusionne `/scans/index.json` et `/data/catalogue-fr.json` (chargement parallèle, l'un peut manquer) ; cartes `o.serie` → mode C, tracking `scanaddiction`.
- Sauvegardes avant modification : `build/avant-traducteur/` ; patch rejouable : `build/patch_site.py`.
- ⚠️ Hors périmètre initial (cahier des charges §3) : Scanaddiction **héberge désormais des scans** → voir §7 juridique.
