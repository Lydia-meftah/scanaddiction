-- ============================================================================
-- Scanaddiction — Schéma de la base de données (Cloudflare D1 / SQLite)
-- ----------------------------------------------------------------------------
-- Modèle relationnel du catalogue. Source de vérité : ce fichier.
-- Les migrations versionnées vivent dans db/migrations/ (wrangler d1 migrations).
-- Convention : identifiants préfixés par source (mdx-, cs-, sm-, ss-, rj-).
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ── Sources de données ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS source (
  code            TEXT PRIMARY KEY,                 -- 'mangadex', 'crunchyscan', ...
  nom             TEXT NOT NULL,                    -- 'MangaDex'
  base_url        TEXT NOT NULL,
  lecteur_integre INTEGER NOT NULL DEFAULT 0,       -- 0/1 : lisible sur le site
  fiable          INTEGER NOT NULL DEFAULT 0,       -- 0/1 : source stable (API officielle)
  actif           INTEGER NOT NULL DEFAULT 1        -- 0/1 : incluse dans le scrape
);

-- ── Séries (œuvres) ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS series (
  id               TEXT PRIMARY KEY,                -- 'mdx-<uuid>'
  source_code      TEXT NOT NULL REFERENCES source(code) ON UPDATE CASCADE,
  mangadex_id      TEXT,                            -- UUID pur (lecteur mode A), nullable
  titre            TEXT NOT NULL,
  slug             TEXT,
  url              TEXT NOT NULL,
  cover            TEXT NOT NULL DEFAULT '',
  type             TEXT NOT NULL DEFAULT 'manga'
                     CHECK (type IN ('manga','manhwa','manhua')),
  statut           TEXT NOT NULL DEFAULT 'en cours'
                     CHECK (statut IN ('en cours','terminé','pause','annulé')),
  synopsis         TEXT NOT NULL DEFAULT '',
  auteur           TEXT NOT NULL DEFAULT '',
  genres           TEXT NOT NULL DEFAULT '[]',      -- tableau JSON (texte)
  note             REAL NOT NULL DEFAULT 0,
  dernier_chapitre REAL NOT NULL DEFAULT 0,
  lecteur_integre  INTEGER NOT NULL DEFAULT 0,      -- 0/1
  first_seen       TEXT NOT NULL,                   -- ISO 8601 UTC — 1re apparition
  last_seen        TEXT NOT NULL,                   -- ISO 8601 UTC — dernier run vu
  updated_at       TEXT NOT NULL                    -- ISO 8601 UTC — dernière modif
);

CREATE INDEX IF NOT EXISTS idx_series_source  ON series(source_code);
CREATE INDEX IF NOT EXISTS idx_series_type    ON series(type);
CREATE INDEX IF NOT EXISTS idx_series_statut  ON series(statut);
CREATE INDEX IF NOT EXISTS idx_series_titre   ON series(titre COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_series_lastseen ON series(last_seen);

-- ── Chapitres (optionnel — alimenté plus tard / cache lecteur) ───────────────
CREATE TABLE IF NOT EXISTS chapter (
  id           TEXT PRIMARY KEY,                    -- hash(series_id|numero) ou id source
  series_id    TEXT NOT NULL REFERENCES series(id) ON DELETE CASCADE,
  numero       REAL NOT NULL,
  titre        TEXT NOT NULL DEFAULT '',
  url          TEXT NOT NULL,
  published_at TEXT,
  updated_at   TEXT NOT NULL,
  UNIQUE (series_id, numero)
);

CREATE INDEX IF NOT EXISTS idx_chapter_series ON chapter(series_id);

-- ── Journal des runs ETL (observabilité) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS scrape_run (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at     TEXT NOT NULL,
  finished_at    TEXT,
  status         TEXT NOT NULL CHECK (status IN ('success','partial','failed')),
  total_series   INTEGER NOT NULL DEFAULT 0,
  inserted       INTEGER NOT NULL DEFAULT 0,
  updated        INTEGER NOT NULL DEFAULT 0,
  sources_ok     TEXT NOT NULL DEFAULT '[]',        -- JSON
  sources_failed TEXT NOT NULL DEFAULT '[]',        -- JSON
  duration_sec   REAL,
  notes          TEXT NOT NULL DEFAULT ''
);
