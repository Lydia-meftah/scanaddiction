#!/usr/bin/env python3
"""
scraper.py — Catalogue francophone scantrad
Sources :
  - MangaDex REST API  → manga avec traduction française disponible
  - Crunchyscan        → sitemaps XML (pas de Cloudflare sur les sitemaps)
  - Scan-Manga         → page "En cours" + meta tags OG (server-side rendered)
  - Sushiscan          → wp-sitemap-posts-manga-N.xml (bypass Cloudflare)
  - Raijin-Scans       → wp-sitemap-posts-wp-manga-N.xml (slugs uniques extraits)
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests

# ──────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────
OUTPUT_FILE  = os.path.join(os.path.dirname(__file__), "data", "catalogue-fr.json")
HTTP_TIMEOUT = 30
DELAY        = 1.2

UA = "Scanaddiction/1.0 (catalogue-fr; contact github.com/Lydia-meftah)"
HEADERS = {"User-Agent": UA}


# ══════════════════════════════════════════════════════════
# SOURCE 1 — MangaDex (API officielle, traductions FR)
# ══════════════════════════════════════════════════════════
MDX_BASE       = "https://api.mangadex.org"
MDX_LIMIT      = 100
MDX_MAX_OFFSET = 500   # 5 pages × 100 = 500 œuvres

MDX_STATUT = {
    "ongoing":   "en cours",
    "completed": "terminé",
    "hiatus":    "pause",
    "cancelled": "annulé",
}

MDX_TYPE = {
    "manga":    "manga",
    "manhwa":   "manhwa",
    "manhua":   "manhua",
    "doujinshi":"manga",
    "one_shot": "manga",
}


def clean(txt):
    if not txt:
        return ""
    txt = re.sub(r"<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def mdx_fetch(offset):
    params = [
        ("availableTranslatedLanguage[]", "fr"),
        ("limit", MDX_LIMIT),
        ("offset", offset),
        ("order[followedCount]", "desc"),
        ("includes[]", "cover_art"),
        ("includes[]", "author"),
        ("contentRating[]", "safe"),
        ("contentRating[]", "suggestive"),
    ]
    try:
        r = requests.get(f"{MDX_BASE}/manga", params=params,
                         headers=HEADERS, timeout=HTTP_TIMEOUT)
        if r.status_code == 429:
            print("  ⏳ Rate-limit MangaDex, pause 60s…")
            time.sleep(60)
            r = requests.get(f"{MDX_BASE}/manga", params=params,
                             headers=HEADERS, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            print(f"  ❌ MangaDex HTTP {r.status_code} (offset {offset})")
            return []
        return r.json().get("data", [])
    except Exception as e:
        print(f"  ❌ MangaDex erreur (offset {offset}): {e}")
        return []


def mdx_cover(manga_id, rels):
    for rel in (rels or []):
        if rel.get("type") == "cover_art":
            fname = (rel.get("attributes") or {}).get("fileName", "")
            if fname:
                return f"https://uploads.mangadex.org/covers/{manga_id}/{fname}.512.jpg"
    return ""


def mdx_title(attrs):
    t = attrs.get("title") or {}
    for lang in ("fr", "en", "ja-ro", "ja"):
        if t.get(lang):
            return t[lang]
    for d in (attrs.get("altTitles") or []):
        for lang in ("fr", "en"):
            if d.get(lang):
                return d[lang]
    return next(iter(t.values()), "Sans titre")


def mdx_author(rels):
    for rel in (rels or []):
        if rel.get("type") in ("author", "artist"):
            n = (rel.get("attributes") or {}).get("name", "")
            if n:
                return n
    return ""


def mdx_genres(attrs):
    return [
        (t.get("attributes", {}).get("name", {}).get("fr")
         or t.get("attributes", {}).get("name", {}).get("en", ""))
        for t in (attrs.get("tags") or [])
        if t.get("attributes", {}).get("group") == "genre"
    ][:6]


def mdx_map(m):
    attrs = m.get("attributes") or {}
    mid   = m["id"]
    rels  = m.get("relationships") or []
    desc  = attrs.get("description") or {}
    syn   = clean(desc.get("fr") or desc.get("en") or "")[:600]
    typ   = attrs.get("originalLanguage", "")
    return {
        "id":              f"mdx-{mid}",
        "mangadexId":      mid,          # UUID pur pour le lecteur
        "titre":           mdx_title(attrs),
        "url":             f"https://mangadex.org/title/{mid}",
        "cover":           mdx_cover(mid, rels),
        "type":            MDX_TYPE.get(typ, "manga") if typ in MDX_TYPE
                           else ("manhwa" if typ == "ko" else "manga"),
        "statut":          MDX_STATUT.get(attrs.get("status", ""), "en cours"),
        "synopsis":        syn,
        "genres":          mdx_genres(attrs),
        "auteur":          mdx_author(rels),
        "note":            0.0,
        "dernierChapitre": 0,
        "sourceNom":       "MangaDex",
        "sourceUrl":       "https://mangadex.org",
        "lecteurIntegre":  True,         # le catalogue peut afficher le lecteur
    }


def scrape_mangadex():
    print("\n🌐 [MangaDex] API — manga traduits en français")
    items, seen = [], set()
    for offset in range(0, MDX_MAX_OFFSET + 1, MDX_LIMIT):
        data = mdx_fetch(offset)
        if not data:
            print(f"  fin à offset {offset}")
            break
        new = [m for m in data if m["id"] not in seen]
        for m in new:
            seen.add(m["id"])
            items.append(mdx_map(m))
        print(f"  offset {offset:3d}: {len(data)} → cumul {len(items)}")
        time.sleep(DELAY)
    print(f"  → {len(items)} œuvres MangaDex")
    return items


# ══════════════════════════════════════════════════════════
# SOURCE 2 — Crunchyscan (sitemaps XML publics)
# ══════════════════════════════════════════════════════════
CRUNCHYSCAN_BASE = "https://crunchyscan.fr"
CRUNCHYSCAN_MAPS = 4


def title_from_slug(slug):
    return re.sub(r"\b(\w)", lambda m: m.group(1).upper(),
                  slug.replace("-", " "))


def scrape_crunchyscan():
    print(f"\n🗺  [Crunchyscan] Sitemaps XML (1 à {CRUNCHYSCAN_MAPS})")
    items, seen = [], set()
    for i in range(1, CRUNCHYSCAN_MAPS + 1):
        url = f"{CRUNCHYSCAN_BASE}/sitemap-series-{i}.xml"
        try:
            r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            if r.status_code != 200:
                print(f"  sitemap-{i}: HTTP {r.status_code}")
                continue
            slugs = re.findall(r'/lecture-en-ligne/([^<\s"\'/?]+)', r.text)
            print(f"  sitemap-{i}: {len(slugs)} slugs")
            for slug in slugs:
                slug = slug.strip("/")
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                items.append({
                    "id":              f"cs-{slug}",
                    "titre":           title_from_slug(slug),
                    "url":             f"{CRUNCHYSCAN_BASE}/lecture-en-ligne/{slug}",
                    "cover":           f"{CRUNCHYSCAN_BASE}/upload/manga/{slug}/cover.jpg",
                    "type":            "manhwa",
                    "statut":          "en cours",
                    "synopsis":        "",
                    "genres":          [],
                    "auteur":          "",
                    "note":            0.0,
                    "dernierChapitre": 0,
                    "sourceNom":       "Crunchyscan",
                    "sourceUrl":       CRUNCHYSCAN_BASE,
                    "lecteurIntegre":  False,
                })
        except Exception as e:
            print(f"  sitemap-{i}: erreur {e}")
        time.sleep(DELAY)
    print(f"  → {len(items)} œuvres Crunchyscan")
    return items


# ══════════════════════════════════════════════════════════
# SOURCE 3 — Scan-Manga (page "En cours" + meta OG)
# ══════════════════════════════════════════════════════════
SM_BASE        = "https://www.scan-manga.com"
SM_EN_COURS    = f"{SM_BASE}/scanlation/En-cours.html"
SM_MAX_SERIES  = 200   # limite pour tenir dans le timeout Actions

SM_TYPE_MAP = {
    "manga":   "manga",
    "manhwa":  "manhwa",
    "manhua":  "manhua",
    "bd":      "manga",
    "novel":   "manga",
    "webtoon": "manhwa",
}

SM_DEMO_GENRE = {
    "shonen": "Shonen", "seinen": "Seinen", "shojo": "Shojo",
    "josei": "Josei", "yaoi": "Yaoi", "yuri": "Yuri",
    "isekai": "Isekai", "ecchi": "Ecchi",
}


def sm_fetch(url):
    """Requête directe — les meta tags sont rendus côté serveur."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        if r.status_code == 200:
            return r.text
        print(f"  SM HTTP {r.status_code} — {url[:60]}")
    except Exception as e:
        print(f"  SM erreur: {e} — {url[:60]}")
    return None


def sm_parse_detail(html, url):
    """Extrait cover + metadata depuis les meta OG (server-side rendered)."""
    # og:image → cover
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
    cover = m.group(1).strip() if m else ""

    # og:title ou title → "Lire {titre} VF - Manga / Shojo (2020 - Auteur)"
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if not m:
        m = re.search(r'<title>([^<]+)</title>', html, re.I)
    raw_title = m.group(1).strip() if m else ""

    # Nettoyer le titre : "Lire XXX VF - Manga / Shojo (...)" → "XXX"
    titre = re.sub(r'^Lire\s+', '', raw_title, flags=re.I)
    titre = re.sub(r'\s+VF\s*[-–].*$', '', titre, flags=re.I).strip()
    titre = clean(titre) or raw_title.strip()

    # description → "Manga / Shojo (2020 - Auteur)" ou "Manhwa / ..."
    m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    desc = m.group(1).strip() if m else ""

    # Type depuis description
    type_str = "manga"
    for kw in ("manhwa", "manhua", "webtoon", "bd", "novel", "manga"):
        if kw in desc.lower():
            type_str = SM_TYPE_MAP.get(kw, "manga")
            break

    # Genre depuis la démographie
    genres = []
    desc_low = desc.lower()
    for kw, label in SM_DEMO_GENRE.items():
        if kw in desc_low:
            genres.append(label)
    genres = genres[:3]

    # Auteur : pattern "(2020 - Auteur)" ou "(Auteur)"
    m = re.search(r'\(\d{4}\s*[-–]\s*([^)]+)\)', desc)
    if not m:
        m = re.search(r'\(([^)]{3,40})\)\s*$', desc)
    auteur = m.group(1).strip() if m else ""

    # ID depuis l'URL
    id_m = re.search(r'/(\d+(?:-\d+)?)/[^/]+\.html', url)
    sm_id = id_m.group(1) if id_m else re.sub(r'[^\w]', '-', url)

    return {
        "id":              f"sm-{sm_id}",
        "titre":           titre or url.split('/')[-1].replace('.html','').replace('-',' ').title(),
        "url":             url,
        "cover":           cover,
        "type":            type_str,
        "statut":          "en cours",
        "synopsis":        "",
        "genres":          genres,
        "auteur":          auteur,
        "note":            0.0,
        "dernierChapitre": 0,
        "sourceNom":       "Scan-Manga",
        "sourceUrl":       SM_BASE,
        "lecteurIntegre":  False,
    }


def scrape_scan_manga():
    print(f"\n📖 [Scan-Manga] Séries en cours ({SM_EN_COURS})")

    # 1. Récupérer la liste des séries en cours
    html_list = sm_fetch(SM_EN_COURS)
    if not html_list:
        print("  ❌ Page inaccessible")
        return []

    # Trouver tous les liens de séries : /{id}/{slug}.html ou /{id}-{id2}/{slug}.html
    hrefs = list(dict.fromkeys(
        re.findall(r'href=["\'](?:https?://www\.scan-manga\.com)?(/\d+(?:-\d+)?/[A-Za-z0-9][^"\'<>\s]+\.html)', html_list)
    ))
    print(f"  Liens trouvés dans le HTML: {len(hrefs)}")

    if not hrefs:
        print("  ⚠ Page JS-only détectée, tentative sur page alternative…")
        # Fallback : récupérer la page principale et extraire les séries récentes
        html_list = sm_fetch(f"{SM_BASE}/?home")
        if html_list:
            hrefs = list(dict.fromkeys(
                re.findall(r'href=["\'](?:https?://www\.scan-manga\.com)?(/\d+(?:-\d+)?/[A-Za-z0-9][^"\'<>\s]+\.html)', html_list)
            ))
            print(f"  Liens depuis homepage: {len(hrefs)}")

    if not hrefs:
        print("  ❌ Aucun lien de série trouvé")
        return []

    # Limiter
    hrefs = hrefs[:SM_MAX_SERIES]
    print(f"  → {len(hrefs)} séries à traiter")

    # 2. Récupérer les détails de chaque série
    items = []
    for i, href in enumerate(hrefs, 1):
        url = SM_BASE + href if href.startswith('/') else href
        html = sm_fetch(url)
        if html:
            item = sm_parse_detail(html, url)
            if item["titre"]:
                items.append(item)
                if i % 20 == 0:
                    print(f"  [{i}/{len(hrefs)}] {item['titre'][:40]}")
        time.sleep(DELAY)

    print(f"  → {len(items)} œuvres Scan-Manga")
    return items


# ══════════════════════════════════════════════════════════
# SOURCE 4 — Sushiscan (wp-sitemap-posts-manga-N.xml)
# ══════════════════════════════════════════════════════════
SUSHISCAN_BASE = "https://sushiscan.net"
SUSHISCAN_MAPS = 3   # wp-sitemap-posts-manga-1.xml … 3.xml


def scrape_sushiscan():
    print(f"\n🍣 [Sushiscan] Sitemaps WordPress (1 à {SUSHISCAN_MAPS})")
    items, seen = [], set()
    for i in range(1, SUSHISCAN_MAPS + 1):
        url = f"{SUSHISCAN_BASE}/wp-sitemap-posts-manga-{i}.xml"
        try:
            r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            if r.status_code != 200:
                print(f"  sitemap-{i}: HTTP {r.status_code}")
                continue
            slugs = re.findall(
                r'https?://sushiscan\.net/catalogue/([^/<\s"\']+)/', r.text
            )
            print(f"  sitemap-{i}: {len(slugs)} slugs")
            for slug in slugs:
                slug = slug.strip("/")
                if not slug or slug in seen:
                    continue
                seen.add(slug)
                items.append({
                    "id":              f"ss-{slug}",
                    "titre":           title_from_slug(slug),
                    "url":             f"{SUSHISCAN_BASE}/catalogue/{slug}/",
                    "cover":           "",   # Cloudflare bloque les pages individuelles
                    "type":            "manga",
                    "statut":          "en cours",
                    "synopsis":        "",
                    "genres":          [],
                    "auteur":          "",
                    "note":            0.0,
                    "dernierChapitre": 0,
                    "sourceNom":       "Sushiscan",
                    "sourceUrl":       SUSHISCAN_BASE,
                    "lecteurIntegre":  False,
                })
        except Exception as e:
            print(f"  sitemap-{i}: erreur {e}")
        time.sleep(DELAY)
    print(f"  → {len(items)} œuvres Sushiscan")
    return items


# ══════════════════════════════════════════════════════════
# SOURCE 5 — Raijin-Scans (sitemaps chapitres → slugs séries uniques)
# ══════════════════════════════════════════════════════════
RAIJIN_BASE = "https://raijin-scans.fr"
RAIJIN_MAPS = 30   # pages de chapitres — extraire les slugs séries uniques


def scrape_raijin():
    print(f"\n⚔️  [Raijin-Scans] Sitemaps chapitres (1 à {RAIJIN_MAPS}) → séries uniques")
    seen_slugs = set()
    items = []
    for i in range(1, RAIJIN_MAPS + 1):
        url = f"{RAIJIN_BASE}/wp-sitemap-posts-wp-manga-{i}.xml"
        try:
            r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
            if r.status_code != 200:
                print(f"  page-{i}: HTTP {r.status_code} — arrêt")
                break
            # Extraire slugs depuis /manga/{slug}/{num}/
            slugs = re.findall(
                r'raijin-scans\.fr/manga/([^/<\s"\']+)/\d+/', r.text
            )
            new = 0
            for slug in slugs:
                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    items.append({
                        "id":              f"rj-{slug}",
                        "titre":           title_from_slug(slug),
                        "url":             f"{RAIJIN_BASE}/manga/{slug}/",
                        "cover":           "",
                        "type":            "manhwa",
                        "statut":          "en cours",
                        "synopsis":        "",
                        "genres":          [],
                        "auteur":          "",
                        "note":            0.0,
                        "dernierChapitre": 0,
                        "sourceNom":       "Raijin-Scans",
                        "sourceUrl":       RAIJIN_BASE,
                        "lecteurIntegre":  False,
                    })
                    new += 1
            print(f"  page-{i:3d}: {new} nouveaux slugs (cumul {len(items)})")
        except Exception as e:
            print(f"  page-{i}: erreur {e}")
        time.sleep(DELAY)
    print(f"  → {len(items)} séries Raijin-Scans")
    return items


# ══════════════════════════════════════════════════════════
# Catalogue
# ══════════════════════════════════════════════════════════
def build_catalogue(all_items):
    unique = {}
    for it in all_items:
        key = it["id"]
        if key not in unique:
            unique[key] = it
    oeuvres = sorted(unique.values(), key=lambda x: x["titre"].lower())
    return {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "total":      len(oeuvres),
        "sources":    sorted({i["sourceNom"] for i in oeuvres}),
        "oeuvres":    oeuvres,
    }


def main():
    print("🚀 Scanaddiction — Scraper catalogue francophone")
    print("=" * 55)

    items = []
    items += scrape_mangadex()
    items += scrape_crunchyscan()
    items += scrape_scan_manga()
    items += scrape_sushiscan()
    items += scrape_raijin()

    catalogue = build_catalogue(items)
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogue, f, ensure_ascii=False, indent=2)

    print("=" * 55)
    print(f"✅ {catalogue['total']} œuvres — {catalogue['sources']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            