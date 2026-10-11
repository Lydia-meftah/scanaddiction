"""Écritures de sortie : JSON (compatibilité front / CDN) + SQL d'upsert D1."""
import json
import os
from datetime import datetime, timezone

from . import config

# code source → (Nom lisible, base_url) pour le JSON hérité
SOURCE_META = {
    "mangadex": ("MangaDex", "https://mangadex.org"),
    "crunchyscan": ("Crunchyscan", "https://crunchyscan.fr"),
    "scan-manga": ("Scan-Manga", "https://www.scan-manga.com"),
    "sushiscan": ("Sushiscan", "https://sushiscan.net"),
    "raijin": ("Raijin-Scans", "https://raijin-scans.fr"),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def save_raw(name, text):
    os.makedirs(config.RAW_DIR, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    _atomic_write(os.path.join(config.RAW_DIR, f"{name}-{day}.raw"), text)


def write_json(records):
    """Produit data/catalogue-fr.json au format attendu par le front (clés héritées)."""
    oeuvres = []
    for r in sorted(records, key=lambda x: x["titre"].lower()):
        nom, src_url = SOURCE_META.get(r["source_code"], (r["source_code"], ""))
        o = {
            "id": r["id"], "titre": r["titre"], "url": r["url"], "cover": r["cover"],
            "type": r["type"], "statut": r["statut"], "synopsis": r["synopsis"],
            "genres": r["genres"], "auteur": r["auteur"], "note": r["note"],
            "dernierChapitre": r["dernier_chapitre"], "sourceNom": nom,
            "sourceUrl": src_url, "lecteurIntegre": bool(r["lecteur_integre"]),
        }
        if r.get("mangadex_id"):
            o["mangadexId"] = r["mangadex_id"]
        oeuvres.append(o)
    catalogue = {
        "lastUpdate": _now(), "total": len(oeuvres),
        "sources": sorted({SOURCE_META.get(r["source_code"], (r["source_code"],))[0] for r in records}),
        "oeuvres": oeuvres,
    }
    _atomic_write(config.CATALOGUE_JSON, json.dumps(catalogue, ensure_ascii=False, indent=2))
    return catalogue


def _sql(v):
    """Échappe une valeur pour un littéral SQL (fichier exécuté par wrangler, sans params)."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def write_upsert_sql(records, run_meta):
    """Génère build/upsert.sql : upsert des séries + insertion du run (idempotent)."""
    now = _now()
    lines = ["PRAGMA foreign_keys = ON;", "BEGIN TRANSACTION;"]
    for r in records:
        genres = json.dumps(r["genres"], ensure_ascii=False)
        cols = ("id, source_code, mangadex_id, titre, slug, url, cover, type, statut, "
                "synopsis, auteur, genres, note, dernier_chapitre, lecteur_integre, "
                "first_seen, last_seen, updated_at")
        vals = ", ".join(_sql(x) for x in [
            r["id"], r["source_code"], r.get("mangadex_id"), r["titre"], r.get("slug"),
            r["url"], r["cover"], r["type"], r["statut"], r["synopsis"], r["auteur"],
            genres, r["note"], r["dernier_chapitre"], r["lecteur_integre"], now, now, now,
        ])
        lines.append(
            f"INSERT INTO series ({cols}) VALUES ({vals}) "
            "ON CONFLICT(id) DO UPDATE SET "
            "titre=excluded.titre, url=excluded.url, cover=excluded.cover, type=excluded.type, "
            "statut=excluded.statut, synopsis=excluded.synopsis, auteur=excluded.auteur, "
            "genres=excluded.genres, note=excluded.note, dernier_chapitre=excluded.dernier_chapitre, "
            "lecteur_integre=excluded.lecteur_integre, last_seen=excluded.last_seen, "
            "updated_at=excluded.updated_at;"
        )
    lines.append(
        "INSERT INTO scrape_run (started_at, finished_at, status, total_series, "
        "sources_ok, sources_failed, duration_sec, notes) VALUES ("
        f"{_sql(run_meta['started_at'])}, {_sql(run_meta['finished_at'])}, "
        f"{_sql(run_meta['status'])}, {_sql(run_meta['total_series'])}, "
        f"{_sql(json.dumps(run_meta['sources_ok']))}, {_sql(json.dumps(run_meta['sources_failed']))}, "
        f"{_sql(run_meta['duration_sec'])}, {_sql(run_meta.get('notes',''))});"
    )
    lines.append("COMMIT;")
    _atomic_write(config.UPSERT_SQL, "\n".join(lines) + "\n")
    return config.UPSERT_SQL
