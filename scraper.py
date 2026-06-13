#!/usr/bin/env python3
"""
scraper.py — Catalogue francophone scantrad
Génère data/catalogue-fr.json depuis plusieurs sources FR.

Sources :
  - crunchyscan.fr   → sitemaps XML  (1800+ séries, mode rapide)
  - raijin-scans.fr  → WordPress/Madara
  - sushiscan.net    → WordPress/Madara
  - manga-scantrad.io→ WordPress/Madara
  - phenixscans.fr   → WordPress/Madara

Usage : python scraper.py
"""

import json
import re
import time
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

try:
    import cloudscraper
    _http = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    print("✅ cloudscraper chargé")
except ImportError:
    import requests
    _http = requests.Session()
    _http.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    print("⚠ cloudscraper absent, utilisation de requests")

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────
SOURCES = [
    # ── Crunchyscan : sitemap XML → slugs → données dérivées ──
    {
        "nom":           "Crunchyscan",
        "url":           "https://crunchyscan.fr",
        "type":          "crunchyscan",
        "sitemap_count": 4,      # sitemap-series-1.xml … -4.xml
    },
    # ── Sites WordPress / Madara ───────────────────────────────
    {
        "nom": "Raijin Scans",
        "url": "https://raijin-scans.fr",
        "type": "madara",
    },
    {
        "nom": "Sushiscan",
        "url": "https://sushiscan.net",
        "type": "madara",
    },
    {
        "nom": "Manga Scantrad",
        "url": "https://manga-scantrad.io",
        "type": "madara",
    },
    {
        "nom": "Phénix Scans",
        "url": "https://www.phenixscans.fr",
        "type": "madara",
    },
]

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "catalogue-fr.json")
DELAY       = 1.5   # délai entre requêtes (politesse)
MAX_PAGES   = 10    # pages de liste Madara max
PER_PAGE    = 36    # items par page Madara
TIMEOUT     = 20

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
}


# ──────────────────────────────────────────────────────────────
# HTTP
# ──────────────────────────────────────────────────────────────
def fetch(url, retries=2):
    """GET url, retourne le texte ou None. Log le status pour debug."""
    for attempt in range(retries):
        try:
            r = _http.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            print(f"    HTTP {r.status_code}  {len(r.text):>7} chars  {url[:70]}")
            if r.status_code == 200:
                return r.text
            if r.status_code in (429, 503) and attempt < retries - 1:
                time.sleep(5)
        except Exception as e:
            print(f"    ⚠ erreur {url[:70]}: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def strip_tags(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()

def clean_text(s):
    if not s:
        return ""
    for old, new in [
        ("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),
        ("&#039;","'"),("&rsquo;","'"),("&nbsp;"," "),("\xa0"," "),
    ]:
        s = s.replace(old, new)
    return re.sub(r"\s+", " ", s).strip()

def slug_from_url(url):
    for pat in (r"/manga/([^/?#]+)", r"/lecture-en-ligne/([^/?#]+)"):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return urlparse(url).path.strip("/").replace("/", "-")

def title_from_slug(slug):
    """Titre lisible depuis un slug (fallback si page inaccessible)."""
    return re.sub(r"\b(\w)", lambda m: m.group(1).upper(),
                  slug.replace("-", " "))


# ──────────────────────────────────────────────────────────────
# Scraper Crunchyscan — mode sitemap uniquement
# ──────────────────────────────────────────────────────────────
def scrape_source_crunchyscan(source):
    """
    Parse les sitemaps XML pour obtenir tous les slugs.
    Construit les items sans fetcher les pages détail
    (cover URL est déterministe, titre dérivé du slug).
    → Plus rapide et moins bloquable.
    """
    base  = source["url"]
    n     = source.get("sitemap_count", 4)
    items = []
    seen  = set()

    print(f"\n🌐 [Crunchyscan] Lecture des sitemaps…")
    for i in range(1, n + 1):
        url = f"{base}/sitemap-series-{i}.xml"
        print(f"  🗺  sitemap-series-{i}.xml")
        xml = fetch(url)
        if not xml:
            print(f"    ⚠ inaccessible, on continue")
            time.sleep(DELAY)
            continue

        slugs = re.findall(r'/lecture-en-ligne/([^<\s"\']+)', xml)
        print(f"    → {len(slugs)} slugs")

        for slug in slugs:
            slug = slug.strip("/")
            if not slug or slug in seen:
                continue
            seen.add(slug)
            titre = title_from_slug(slug)
            items.append({
                "id":             slug,
                "titre":          titre,
                "url":            f"{base}/lecture-en-ligne/{slug}",
                "cover":          f"{base}/upload/manga/{slug}/cover.jpg",
                "type":           "manhwa",
                "statut":         "en cours",
                "synopsis":       "",
                "genres":         [],
                "auteur":         "",
                "note":           0.0,
                "dernierChapitre": 0,
                "sourceNom":      source["nom"],
                "sourceUrl":      source["url"],
            })
        time.sleep(DELAY)

    print(f"  → Total: {len(items)} œuvres Crunchyscan")
    return items


# ──────────────────────────────────────────────────────────────
# Scraper Madara (WordPress)
# ──────────────────────────────────────────────────────────────
def scrape_madara_list(base_url, page=1):
    url  = f"{base_url}/page/{page}/?post_type=wp-manga&s=&sort=recently_added"
    print(f"  📄 page {page}: {url}")
    html = fetch(url)
    if not html:
        return []

    items = []
    seen  = set()

    # Cherche les liens h3.h5 → /manga/
    manga_links = re.findall(
        r'<h3[^>]*class=["\'][^"\']*h5[^"\']*["\'][^>]*>\s*<a\s+href=["\']([^"\']+/manga/[^"\']+)["\'][^>]*>([^<]+)</a>',
        html, re.I | re.S
    )
    for href, titre in manga_links:
        href  = href.strip()
        titre = clean_text(titre)
        if not titre or href in seen:
            continue
        seen.add(href)
        idx    = html.find(href)
        nearby = html[max(0, idx - 800):idx + 200].lower()

        cover = ""
        for attr in ("data-src", "src"):
            m = re.search(rf'{attr}=["\']([^"\']+\.(?:jpg|png|webp)[^"\']*)["\']',
                          html[max(0, idx-800):idx+200], re.I)
            if m:
                cover = m.group(1)
                break

        type_str = "manhwa"
        for t in ("manhwa", "manhua", "webtoon", "manga"):
            if t in nearby:
                type_str = t
                break

        statut = "en cours"
        if any(k in nearby for k in ("terminé","completed","finished")):
            statut = "terminé"
        elif any(k in nearby for k in ("pause","hiatus")):
            statut = "pause"

        items.append({"titre": titre, "url": href, "cover": cover,
                      "type": type_str, "statut": statut})

    # Fallback : tout lien /manga/ avec texte
    if not items:
        for href, titre in re.findall(
            r'href=["\']([^"\']+/manga/[^"\']+)["\'][^>]*>\s*(?:<[^>]+>)*\s*([A-ZÀ-Ü][^<]{2,80})',
            html, re.I | re.S
        ):
            titre = clean_text(strip_tags(titre))
            if len(titre) < 2 or href in seen:
                continue
            seen.add(href)
            items.append({"titre": titre, "url": href.strip(),
                          "cover": "", "type": "manhwa", "statut": "en cours"})

    print(f"    → {len(items)} œuvres")
    return items


def scrape_madara_detail(item):
    html = fetch(item["url"])
    if not html:
        return item

    synopsis = ""
    m = re.search(r'class=["\'][^"\']*summary__content[^"\']*["\'][^>]*>(.*?)</div>', html, re.S|re.I)
    if m:
        synopsis = clean_text(strip_tags(m.group(1)))[:600]

    genres = re.findall(r'/genre/([^/"]+)/', html, re.I)
    genres = list(dict.fromkeys(g.lower().replace("-"," ") for g in genres))[:6]

    auteur = ""
    m = re.search(r'class=["\'][^"\']*author-content[^"\']*["\'][^>]*>(.*?)</div>', html, re.S|re.I)
    if m:
        auteur = clean_text(strip_tags(m.group(1)))

    note = 0.0
    m = re.search(r'class=["\'][^"\']*total-votes[^"\']*["\'][^>]*>([0-9.]+)<', html, re.I)
    if not m:
        m = re.search(r'"ratingValue"\s*:\s*"?([0-9.]+)"?', html)
    if m:
        try:
            raw = float(m.group(1))
            note = round(raw / 2, 1) if raw > 5 else round(raw, 1)
        except ValueError:
            pass

    ch_nums = re.findall(r'/chapter-?(\d+(?:\.\d+)?)', html, re.I)
    dernier_ch = 0
    if ch_nums:
        try:
            dernier_ch = int(float(max(ch_nums, key=lambda x: float(x))))
        except (ValueError, TypeError):
            pass

    cover = item.get("cover","")
    m = re.search(r'class=["\'][^"\']*summary_image[^"\']*["\'][^>]*>.*?<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html, re.S|re.I)
    if m:
        cover = m.group(1).strip()

    type_str = item.get("type","manhwa")
    hl = html.lower()
    for t in ("manhwa","manhua","webtoon","manga"):
        if t in hl:
            type_str = t
            break

    statut = item.get("statut","en cours")
    if any(k in hl for k in ("terminé","completed","finished")):
        statut = "terminé"
    elif any(k in hl for k in ("pause","hiatus")):
        statut = "pause"

    print(f"    📖 {item['titre'][:45]} — Ch.{dernier_ch}")
    return {**item, "cover":cover, "synopsis":synopsis, "genres":genres,
            "auteur":auteur, "type":type_str, "statut":statut,
            "note":note, "dernierChapitre":dernier_ch}


def scrape_source_madara(source):
    print(f"\n🌐 [Madara] {source['nom']} ({source['url']})")
    all_items, seen_urls = [], set()

    for page in range(1, MAX_PAGES + 1):
        items = scrape_madara_list(source["url"], page)
        if not items:
            print(f"  ✅ Fin à page {page}")
            break
        new_items = [i for i in items if i["url"] not in seen_urls]
        if not new_items:
            break
        for i in new_items:
            seen_urls.add(i["url"])

        for item in new_items[:PER_PAGE]:
            time.sleep(DELAY)
            enriched = scrape_madara_detail(item)
            enriched["sourceNom"] = source["nom"]
            enriched["sourceUrl"] = source["url"]
            enriched["id"]        = slug_from_url(enriched["url"])
            all_items.append(enriched)

        time.sleep(DELAY)

    print(f"  → Total: {len(all_items)} œuvres pour {source['nom']}")
    return all_items


# ──────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────
def scrape_source(source):
    try:
        if source["type"] == "madara":
            return scrape_source_madara(source)
        if source["type"] == "crunchyscan":
            return scrape_source_crunchyscan(source)
        print(f"  ⚠ type inconnu: {source['type']}")
        return []
    except Exception as e:
        import traceback
        print(f"  ❌ Erreur fatale pour {source['nom']}: {e}")
        traceback.print_exc()
        return []


# ──────────────────────────────────────────────────────────────
# Catalogue final
# ──────────────────────────────────────────────────────────────
def build_catalogue(all_items):
    seen, unique = set(), []
    for item in all_items:
        key = re.sub(r"[^a-z0-9]", "", item["titre"].lower())
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    unique.sort(key=lambda x: x["titre"].lower())
    return {
        "lastUpdate": datetime.now(timezone.utc).isoformat(),
        "total":      len(unique),
        "sources":    sorted({i["sourceNom"] for i in unique}),
        "oeuvres":    unique,
    }


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main():
    print("🚀 Scanaddiction — Scraper catalogue francophone")
    print("=" * 55)

    all_items = []
    for source in SOURCES:
        items = scrape_source(source)
        all_items.extend(items)
        print(f"  📦 Cumul: {len(all_items)} œuvres\n")

    catalogue = build_catalogue(all_items)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogue, f, ensure_ascii=False, indent=2)

    print("=" * 55)
    print(f"✅ {catalogue['total']} œuvres — {', '.join(catalogue['sources'])}")
    print(f"   {catalogue['lastUpdate']}")


if __name__ == "__main__":
    main()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              