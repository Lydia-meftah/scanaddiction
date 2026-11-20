---
description: Audit complet en parallèle (sécurité, SEO/perf, QA, données) puis backlog priorisé par le CTO
---

Agis en CTO (`.claude/agents/cto.md`).

1. Lance **en parallèle, dans un seul message**, quatre agents en mode audit (lecture seule, aucun commit) :
   `securite`, `seo-perf`, `qa`, `data-engineer`. Chacun rend un tableau
   `gravité | fichier:ligne | problème | correction proposée | effort (S/M/L)`.
2. Fusionne les résultats : supprime les doublons, vérifie toi-même les constats critiques et hauts
   (lis le code), écarte ceux qui ne tiennent pas.
3. Priorise : critique > haute > moyenne > basse, puis effort croissant.
4. Produis le backlog sous forme de tickets (format de `cto.md`) avec le rôle responsable.
5. Si `gh` fonctionne, propose de créer les tickets sur GitHub avec le label `agent:<rôle>`. Ne les crée
   qu'après accord, car le label déclenche l'agent automatiquement sur GitHub Actions.
