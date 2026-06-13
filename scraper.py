#!/usr/bin/env python3
"""
scraper.py - Catalogue francophone (sources autorisees)

Ce scraper construit le catalogue a partir d'APIs publiques et autorisees,
concues pour un usage par des applications tierces :

  - AniList GraphQL API (https://anilist.co)  -> metadonnees manga/manhwa/manhua
    (titres, couvertures, synopsis, genres, score, statut, chapitres)

Aucune protection anti-bot n'est contournee : on utilise uniquement des
points d'acces API documentes et destines a etre consommes par des tiers.

Le JSON genere conserve le meme schema que precedemment afin de rester
compatible avec le front-end (data/catalogue-fr.json).
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
ANILIST_URL = "https://graphql.anilist.co"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "catalogue-fr.json")

PER_PAGE = 50          # max autorise par AniList
MAX_PAGES = 6          # 6 * 50 = 300 oeuvres
DELAY = 1.0            # pause entre requetes (respecte le rate-limit AniList)
HTTP_TIMEOUT = 30

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Scanaddiction-catalogue/1.0 (catalogue francophone)",
}

# Requete GraphQL : manga populaires, tries par popularite.
QUERY = """
query ($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(type: MANGA, sort: POPULARITY_DESC) {
      id
      title { romaji english native }
      description(asHtml: false)
      genres
      averageScore
      status
      chapters
      countryOfOrigin
      siteUrl
      coverImage { large }
      staff(perPage: 1) { nodes { name { full } } }
    }
  }
}
"""

# Mapping pays d'origine -> type d'oeuvre
TYPE_PAR_PAYS = {
    "JP": "manga",
    "KR": "manhwa",
    "CN": "manhua",
    "TW": "manhua",
}

STATUT_MAP = {
    "RELEASING": "en cours",
    "FINISHED": "termine",
    "HIATUS": "pause",
    "CANCELLED": "annule",
    "NOT_YET_RELEASED": "a venir",
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def clean_text(txt):
    if not txt:
        return ""
    # AniList renvoie parfois des balises <br>, <i>, etc. dans la description
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def fetch_page(page):
    """Recupere une page de resultats via l'API GraphQL AniList."""
    payload = {"query": QUERY, "variables": {"page": page, "perPage": PER_PAGE}}
    try:
        r = requests.post(ANILIST_URL, json=payload, headers=HEADERS, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            print(f"  AniList HTTP {r.status_code} (page {page})")
            return []
        data = r.json()
        media = data.get("data", {}).get("Page", {}).get("media", [])
        print(f"  AniList page {page}: {len(media)} oeuvres")
        return media
    except Exception as e:
        print(f"  AniList erreur page {page}: {e}")
        return []


def map_media(m):
    """Transforme une oeuvre AniList vers le schema du catalogue."""
    titles = m.get("title") or {}
    titre = titles.get("romaji") or titles.get("english") or titles.get("native") or "Sans titre"

    staff_nodes = (m.get("staff") or {}).get("nodes") or []
    auteur = ""
    if staff_nodes:
        auteur = (staff_nodes[0].get("name") or {}).get("full", "") or ""

    score = m.get("averageScore")
    note = round(score / 10.0, 1) if isinstance(score, (int, float)) else 0.0

    pays = m.get("countryOfOrigin") or "JP"
    type_oeuvre = TYPE_PAR_PAYS.get(pays, "manga")

    statut = STATUT_MAP.get(m.get("status") or "", "en cours")

    cover = (m.get("coverImage") or {}).get("large", "") or ""

    return {
        "id": str(m.get("id", "")),
        "titre": titre,
        "url": m.get("siteUrl", "") or "",
        "cover": cover,
        "type": type_oeuvre,
        "statut": statut,
        "synopsis": clean_text(m.get("description")),
        "genres": m.get("genres") or [],
        "auteur": auteur,
        "note": note,
        "dernierChapitre": m.get("chapters") or 0,
        "sourceNom": "AniList",
        "sourceUrl": "https://anilist.co",
    }


def scrape_anilist():
    """Recupere les oeuvres populaires depuis AniList."""
    print("\n[AniList] Recuperation des metadonnees (API GraphQL autorisee)")
    items = []
    seen = set()
    for page in range(1, MAX_PAGES + 1):
        media = fetch_page(page)
        if not media:
            break
        for m in media:
            mid = m.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            items.append(map_media(m))
        time.sleep(DELAY)
    print(f"-> Total: {len(items)} oeuvres depuis AniList")
    return items


def build_catalogue(all_items):
    """Deduplique et construit la structure finale du catalogue."""
    unique = {}
    for it in all_items:
        key = it.get("id") or it.get("titre")
        if key and key not in unique:
            unique[key] = it
    oeuvres = list(unique.values())
    return {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "total": len(oeuvres),
        "sources": sorted({i["sourceNom"] for i in oeuvres}),
        "oeuvres": oeuvres,
    }


def main():
    print("Scanaddiction - Scraper catalogue francophone")
    print("=" * 55)

    all_items = []
    all_items.extend(scrape_anilist())

    catalogue = build_catalogue(all_items)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogue, f, ensure_ascii=False, indent=2)

    print("=" * 55)
    print(f"Catalogue genere: {OUTPUT_FILE}")
    print(f"{catalogue['total']} oeuvres - sources: {catalogue['sources']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
