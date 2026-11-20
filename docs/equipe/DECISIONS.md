# Journal des décisions

Tenu par l'agent CTO. Une entrée par décision structurante, la plus récente en haut.
Format : contexte → options → décision → conséquences. Une décision n'est remise en cause que par une nouvelle entrée.

---

## D-003 — La fusion sur `main` reste humaine
*2026-11-20 · statut : adoptée*

- **Contexte** : l'équipe IA ouvre et relit des PR en autonomie.
- **Décision** : le CTO approuve par label (`cto:approuvé` / `cto:changements`) ; seule la propriétaire du dépôt fusionne.
- **Conséquences** : pas de fusion automatique. Le label évite aussi la limite GitHub qui empêche un bot d'approuver une PR qu'il a lui-même ouverte.

## D-002 — Tailwind compilé, pas de CDN
*2026-11-20 · statut : adoptée (PR #4)*

- **Décision** : `css/tailwind.css` est généré à partir de `css/tailwind.src.css` et versionné ; `scripts/qualite.sh` vérifie qu'il est à jour.
- **Conséquences** : tout changement de classes impose de régénérer le fichier.

## D-001 — Pas d'aspiration ni de republication de contenus protégés
*2026-11-20 · statut : adoptée*

- **Contexte** : demande d'une équipe chargée d'extraire, traduire et republier des chapitres de sites anglophones.
- **Décision** : refusé. L'OCR et la traduction ne servent qu'aux œuvres dont le site détient les droits.
- **Conséquences** : la mise en conformité du lecteur (proxy vers des sites tiers) est à planifier.
