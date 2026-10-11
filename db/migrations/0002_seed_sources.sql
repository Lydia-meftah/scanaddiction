-- Référentiel des sources. fiable=1 → source stable recommandée (API officielle).
INSERT INTO source (code, nom, base_url, lecteur_integre, fiable, actif) VALUES
  ('mangadex',    'MangaDex',     'https://mangadex.org',    1, 1, 1),
  ('crunchyscan', 'Crunchyscan',  'https://crunchyscan.fr',  0, 0, 1),
  ('scan-manga',  'Scan-Manga',   'https://www.scan-manga.com', 0, 0, 1),
  ('sushiscan',   'Sushiscan',    'https://sushiscan.net',   0, 0, 1),
  ('raijin',      'Raijin-Scans', 'https://raijin-scans.fr', 0, 0, 1)
ON CONFLICT(code) DO UPDATE SET
  nom=excluded.nom, base_url=excluded.base_url,
  lecteur_integre=excluded.lecteur_integre, fiable=excluded.fiable;
