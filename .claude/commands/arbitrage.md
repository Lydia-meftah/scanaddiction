---
description: Le CTO tranche une question technique et la consigne dans DECISIONS.md
argument-hint: <question, ex. "garder catalogue.html ou catalogue-fr.html ?">
---

Agis en CTO (`.claude/agents/cto.md`, section « Trancher »).

Question : **$ARGUMENTS**

1. Lis `docs/equipe/DECISIONS.md` : si la question est déjà tranchée, rappelle la décision et arrête-toi,
   sauf fait nouveau.
2. Examine le code concerné. Si l'avis d'un spécialiste est nécessaire, consulte l'agent du rôle (outil Agent,
   en lecture seule, plusieurs agents en parallèle si besoin).
3. Présente 2 ou 3 options avec leurs coûts, leurs risques et leur effort, puis tranche.
4. Ajoute l'entrée en haut de `docs/equipe/DECISIONS.md` (numéro suivant) sur la branche `agent/cto/decision-<sujet>`,
   puis ouvre la PR.
5. Si la décision implique du travail, propose les tickets correspondants (format de `cto.md`).
