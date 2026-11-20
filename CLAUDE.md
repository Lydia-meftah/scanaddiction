# Scanaddiction — règles du projet (lues par tous les agents IA)

Site communautaire de scantrad francophone. Statique (HTML / CSS / JS vanilla, Tailwind 3 compilé),
hébergé sur Cloudflare Pages + Pages Functions (`functions/api/`). Données JSON dans `data/` et `scans/`.

## Commandes

| Action | Commande |
|---|---|
| Tous les contrôles qualité | `bash scripts/qualite.sh` |
| Régénérer Tailwind (après tout changement de classes) | `npx tailwindcss@3.4.17 -i css/tailwind.src.css -o css/tailwind.css --minify` |
| Serveur local | `npx wrangler pages dev .` (ou `python3 -m http.server 8000` sans les Functions) |
| Vérifier le catalogue | `python3 check_catalogue.py` |

## Règles non négociables

1. **Jamais de commit sur `main`.** Une branche par ticket : `agent/<rôle>/<sujet-court>`.
2. **Une PR = un ticket**, petite et relisible. Description : quoi, pourquoi, comment c'est vérifié.
3. **`bash scripts/qualite.sh` doit passer** avant d'ouvrir une PR.
4. **Aucun secret dans le dépôt** (jetons, clés API). Ils vont dans les secrets GitHub ou Cloudflare.
5. **Droits d'auteur** :
   - ne pas ajouter d'aspiration ni de republication de chapitres d'autres sites ;
   - ne pas contourner de protection anti-robot (Cloudflare, captcha, en-têtes falsifiés) ;
   - l'OCR et la traduction ne s'appliquent qu'aux œuvres dont le site détient les droits (œuvres originales,
     autorisation écrite de l'auteur ou de l'équipe d'origine), tracées dans `scans/index.json` (champ `droits`).
   Toute demande contraire est refusée et remontée au CTO.
6. **Ne touche qu'aux fichiers de ton périmètre** (voir `docs/equipe/EQUIPE.md`). Si un changement déborde,
   signale-le au CTO au lieu de le faire.
7. **Les décisions structurantes** (architecture, dépendance, changement de comportement visible) sont tranchées
   par le CTO et consignées dans `docs/equipe/DECISIONS.md`. Lis ce fichier avant de proposer une alternative
   à une décision déjà prise.
8. **La fusion sur `main` reste humaine.** Le CTO approuve (label `cto:approuvé`) ou demande des changements
   (`cto:changements`), la propriétaire du dépôt fusionne.

## Équipe IA

Agents définis dans `.claude/agents/`, organisation dans `docs/equipe/EQUIPE.md`.
Commandes : `/equipe <objectif>`, `/revue-pr <numéro>`, `/arbitrage <question>`, `/audit`.
