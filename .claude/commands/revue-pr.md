---
description: Revue CTO d'une pull request avec verdict et label
argument-hint: <numéro de PR>
---

Agis en CTO (`.claude/agents/cto.md`). Relis la PR **#$ARGUMENTS**.

1. Récupère le titre, la description et le diff (`gh pr view $ARGUMENTS`, `gh pr diff $ARGUMENTS`). Si `gh pr`
   est refusé, utilise l'API REST : `gh api repos/{owner}/{repo}/pulls/$ARGUMENTS` et `.../files`.
2. Récupère la branche en local et lance `bash scripts/qualite.sh`.
3. Applique la grille de relecture et rédige le verdict au format exact de `cto.md`.
4. Publie le verdict en commentaire de la PR et pose le label `cto:approuvé` ou `cto:changements` (retire l'autre).
5. Ne fusionne pas.
