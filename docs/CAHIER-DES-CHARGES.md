# Cahier des charges — Scanaddiction

> Plateforme communautaire de scantrad amateur francophone.
> Document de cadrage projet — version repartie à neuf.

| | |
|---|---|
| **Projet** | Scanaddiction |
| **Type** | Site web communautaire de lecture de scans (manga / manhwa / manhua) |
| **Propriétaire** | Lydia Meftah |
| **Version du document** | 1.0 — 2026-10-11 |
| **Statut projet** | Reprise à neuf (code existant déployé, cadrage formalisé) |
| **Production** | https://scanaddiction-pages.pages.dev |
| **Dépôt** | github.com/Lydia-meftah/scanaddiction (branche `main` = prod) |

---

## 1. Contexte et vision

Scanaddiction est une plateforme **communautaire de scantrad amateur francophone**. Le
positionnement est volontairement opposé aux gros agrégateurs : **qualité avant quantité**,
œuvres choisies avec soin, lecture intégrée sans redirection parasite.

L'ambition produit tient en trois idées :
- un **catalogue francophone unifié**, agrégé automatiquement depuis plusieurs sources ;
- un **lecteur intégré** qui permet de lire sans quitter le site ;
- une **expérience sobre et rapide**, sans publicité agressive ni surcharge.

## 2. Objectifs

| # | Objectif | Indicateur de réussite |
|---|----------|------------------------|
| O1 | Offrir un catalogue FR à jour quotidiennement | Catalogue regénéré chaque nuit, > 0 œuvre, fraîcheur < 24 h |
| O2 | Permettre la lecture intégrée (sans redirection) | ≥ 2 modes de lecture fonctionnels (MangaDex + proxy) |
| O3 | Rester rapide et léger | Site statique, chargement initial < 2 s |
| O4 | Mesurer l'usage réel | Tracking GA4/GTM opérationnel (IDs réels) |
| O5 | Maîtriser la sécurité et les abus | Headers sécurité + rate limiting + protections CF actives |
| O6 | Impliquer la communauté | Suggestions d'œuvres et canal Discord |

## 3. Périmètre

### Dans le périmètre (in scope)
- Pages publiques : accueil, catalogue, lecteur, œuvre, suggestions, à propos, contact, soutien, mentions légales.
- Agrégation automatique multi-sources du catalogue (scraper + CI).
- Lecteur intégré bi-mode (API MangaDex + proxy serveur pour sites Madara).
- Tracking analytique et événements personnalisés.
- Sécurité applicative (headers, WAF, anti-bot, rate limiting).
- Automatisation : build/déploiement continu, notification Discord.

### Hors périmètre (out of scope) — pour l'instant
- Comptes utilisateurs / authentification / favoris synchronisés.
- Hébergement des images de scans par Scanaddiction (les images restent servies par les sources).
- Application mobile native.
- Back-office d'administration / CMS.
- Système de dons/paiement intégré (page « soutien » informative uniquement).

## 4. Cibles et personas

- **Le lecteur FR** : veut lire manga/manhwa en français, rapidement, sans pop-ups. Parcours clé : accueil → catalogue → lecteur.
- **Le découvreur** : explore par type/statut/genre, cherche la nouveauté. Parcours clé : catalogue (filtres, tri, recherche).
- **Le contributeur** : suggère des œuvres, rejoint le Discord. Parcours clé : suggestions → Discord.
- **L'administratrice (Lydia)** : maintient le catalogue, surveille l'usage et la sécurité.

## 5. Besoins fonctionnels

### 5.1 Accueil (`index.html`)
- Présentation du positionnement (hero), statistiques rapides (nb d'œuvres, sources…).
- Accès direct au catalogue et au formulaire de suggestion.

### 5.2 Catalogue (`catalogue-fr.html`)
- Affichage de toutes les œuvres du fichier `data/catalogue-fr.json`.
- **Filtres** : type (manga/manhwa/manhua), statut, source.
- **Tri** et **recherche** plein texte sur le titre.
- Cartes œuvre avec badge **« ▶ Lire ici »** (lecture intégrée) ou **« ↗ Source »** (lien externe).
- **Routage intelligent** selon la source :
  - MangaDex → `/lecteur-fr.html?id={uuid}`
  - Sushiscan / Raijin / Crunchyscan → `/lecteur-fr.html?src={url_encodée}`
  - Autres → lien externe direct.

### 5.3 Lecteur intégré (`lecteur-fr.html`)
- **Mode A** `?id=` → appelle l'API officielle `api.mangadex.org`.
- **Mode B** `?src=` → appelle le proxy interne `/api/chapter` (sites Madara).
- Navigation chapitre précédent / suivant + sélecteur déroulant de chapitres.
- Barre de progression de lecture ; événements de suivi (voir 5.7).
- **En cas d'erreur** : message d'erreur interne uniquement, **aucune redirection externe**.

### 5.4 Fiche œuvre (`oeuvre.html`)
- Détail d'une œuvre (titre, type, statut, synopsis, genres, auteur, source).

### 5.5 Suggestions (`suggestions.html`)
- Formulaire permettant à la communauté de proposer une œuvre.
- Remontée vers un canal Discord (scénario Make).

### 5.6 Pages statiques
- À propos, contact, soutien, mentions légales, page 404 personnalisée.

### 5.7 Tracking (`js/tracking.js`)
Injecté sur toutes les pages, 12 événements personnalisés :
- **Catalogue** : `search`, `filter_apply`, `sort_apply`, `manga_click`.
- **Lecteur** : `reader_open`, `chapter_loaded`, `chapter_error`, `chapter_navigate`.
- **Engagement** : `scroll_milestone` (25/50/75/100 %), `chapter_complete`, `source_performance`.

## 6. Besoins non fonctionnels

| Domaine | Exigence |
|---------|----------|
| **Performance** | Site 100 % statique, CDN Cloudflare, chargement initial < 2 s. |
| **Disponibilité** | Hébergement Cloudflare Pages (haute dispo), déploiement auto sans coupure. |
| **SEO** | Balises meta/OG, `sitemap.xml`, `robots.txt`, canonical, `lang="fr"`. |
| **Accessibilité** | Contrastes suffisants (thème sombre), navigation clavier, responsive mobile-first. |
| **Sécurité** | CSP stricte, anti-clickjacking, WAF, anti-bot, rate limiting (voir fiche technique). |
| **Confidentialité / RGPD** | Analytics à cadrer (bandeau consentement à prévoir), anonymisation email dans les commits. |
| **Maintenabilité** | Stack simple sans build complexe, catalogue regénéré automatiquement, doc à jour. |
| **Robustesse scraper** | Une source en échec ne doit pas interrompre le scrape global. |

## 7. Points de vigilance juridiques

> À traiter sérieusement avant toute communication/croissance.

- Le scantrad et la rediffusion d'images d'œuvres protégées posent des **questions de droit d'auteur**. Le modèle actuel (lecture intégrée via proxy + agrégation de sources tierces) expose potentiellement à des demandes de retrait (DMCA) voire à des poursuites.
- Recommandations de cadrage : politique de retrait claire, mentions légales complètes, pas d'hébergement direct des scans, prudence sur la monétisation, et idéalement **privilégier les sources disposant de licences** (ex. chapitres officiels) ou les œuvres libres.
- Ce point relève d'une décision de la propriétaire ; il est documenté ici au titre du devoir de conseil, sans jugement.

## 8. Arborescence & parcours

```
/                    Accueil
/catalogue.html      Catalogue (+ /catalogue-fr.html généré)
/lecteur-fr.html     Lecteur intégré (?id= ou ?src=)
/oeuvre.html         Fiche œuvre
/suggestions.html    Suggérer une œuvre  → Discord
/apropos.html /contact.html /soutien.html /mentions-legales.html
/404.html            Page non trouvée
Alias : /manga et /lire → 301 vers /catalogue.html
```

## 9. Lotissement & jalons

| Lot | Contenu | État |
|-----|---------|------|
| **Lot 0 — Socle** | Site statique, pages, déploiement CF Pages, headers sécurité | ✅ Fait |
| **Lot 1 — Catalogue auto** | Scraper multi-sources + GitHub Actions nocturne | ⚙️ Fait (sortie à fiabiliser, catalogue actuellement vide) |
| **Lot 2 — Lecteur intégré** | Lecteur bi-mode + proxy `/api/chapter` | ✅ Fait |
| **Lot 3 — Mesure** | GA4 + GTM avec IDs réels | 🔴 À finaliser (IDs placeholder) |
| **Lot 4 — Durcissement** | Rate limiting, Bot Fight Mode, WAF, DDoS, anonymisation email | 🔴 Actions manuelles à faire |
| **Lot 5 — Communauté** | Suggestions → Discord (Make), modération | ⚙️ Partiel |
| **Lot 6 — Conformité** | Consentement cookies / RGPD, politique de retrait | 🔴 À cadrer |

## 10. Definition of Done

Une fonctionnalité est « terminée » quand : elle est déployée sur `main`, testée en conditions
réelles sur l'URL de prod, sans erreur console bloquante, respectueuse des headers CSP, suivie
par un événement analytics quand pertinent, et documentée dans la fiche technique.

## 11. Risques

| Risque | Impact | Parade |
|--------|--------|--------|
| Sources tierces qui changent de structure / bloquent le scrape | Catalogue vide ou partiel | Scrape tolérant aux pannes + supervision + fallback lien externe |
| Blocage Cloudflare côté sources | Lecture intégrée KO | Proxy multi-méthodes d'extraction + message d'erreur propre |
| Abus / scraping du proxy | Charge, coût, blocage | Rate limiting + whitelist domaines + no-store |
| Exposition juridique (droits d'auteur) | Retrait / litige | Voir §7 |
| IDs analytics placeholder | Pas de données | Lot 3 à clôturer |

---

*Document de cadrage — à faire vivre au fil du projet. Détail d'implémentation : voir `docs/SPECS-TECHNIQUES.md`.*
