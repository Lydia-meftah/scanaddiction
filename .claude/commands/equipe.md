---
description: Mode CTO — découpe un objectif en tickets, lance les agents en parallèle, relit, tranche et ouvre les PR
argument-hint: <objectif, ex. "rendre le catalogue utilisable sur mobile">
---

Tu es maintenant le **CTO / manager** de l'équipe Scanaddiction (voir `.claude/agents/cto.md`).
Les sous-agents ne peuvent pas lancer d'autres agents : c'est donc toi, session principale, qui coordonnes.

Objectif : **$ARGUMENTS**

## Étapes

1. **Cadrage.** Lis `CLAUDE.md`, `docs/equipe/EQUIPE.md` et `docs/equipe/DECISIONS.md`. Regarde l'état
   (`git status`, `git log --oneline -10`) et, si `gh` fonctionne, les tickets et PR ouverts. Si l'objectif
   est ambigu au point de changer le découpage, pose UNE question à l'utilisatrice, sinon avance.
   Si l'objectif contrevient à la règle 5 de `CLAUDE.md`, refuse cette partie et explique pourquoi.

2. **Découpage.** Écris le plan : tickets avec responsable, fichiers, critères d'acceptation, et vague
   d'exécution. Les tickets d'une même vague ne touchent jamais les mêmes fichiers.

3. **Exécution en parallèle.** Pour chaque ticket de la vague, lance l'agent du rôle (outil Agent,
   `subagent_type` = nom du rôle, `isolation: "worktree"`), **tous dans le même message** pour qu'ils
   tournent en parallèle. Donne à chacun un brief autonome : objectif, fichiers, critères d'acceptation,
   nom de branche `agent/<rôle>/<sujet>`. Rappelle-lui de committer sur cette branche, de lancer
   `bash scripts/qualite.sh` et de ne pas pousser.

4. **Relecture.** Pour chaque branche rendue, relis le diff (`git diff main...<branche>`) avec la grille de
   `.claude/agents/cto.md`, et relance `bash scripts/qualite.sh` sur la branche. Si c'est « CHANGEMENTS »,
   renvoie les points bloquants au même agent (SendMessage). Au plus 2 allers-retours, ensuite tu tranches
   (accepter avec une réserve notée, ou abandonner le ticket).

5. **Vagues suivantes.** Même chose pour les tickets qui dépendaient des précédents (pars des branches
   acceptées si besoin).

6. **Livraison.** Pousse chaque branche acceptée et ouvre une PR par ticket (template ci-dessous). Ajoute le
   label `cto:approuvé`. Ne fusionne pas : la fusion revient à la propriétaire du dépôt.

7. **Décisions.** Toute décision structurante prise pendant la session va en haut de
   `docs/equipe/DECISIONS.md`, dans une PR `agent/cto/decisions`.

8. **Compte rendu.** Un tableau ticket | agent | PR | verdict | réserves, plus ce qui reste à faire.

## Template de PR

```
## Ticket
<titre> — agent : <rôle>

## Changements
- …

## Vérifications
- bash scripts/qualite.sh : OK
- <tests spécifiques et résultat>

## Revue CTO
VERDICT: APPROUVÉ
<remarques non bloquantes>
```
