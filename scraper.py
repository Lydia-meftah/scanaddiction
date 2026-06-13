#!/usr/bin/env python3
"""
scraper.py — Catalogue francophone scantrad
Utilise FlareSolverr (service Docker) pour contourner Cloudflare.
FlareSolverr lance un vrai Chromium headless avec undetected-chromedriver
→ résout les JS challenges Cloudflare.

Fallback: requests direct si FlareSolverr indisponible.

Sources :
  - crunchyscan.fr   (sitemaps XML → 1800+ séries, mode rapide)
  - raijin-scans.fr  (WordPress/Madara)
  - sushiscan.net    (WordPress/Madara)
  - manga-scantrad.io(WordPress/Madara)
  - phenixscans.fr   (WordPress/Madara)
"""

import json
import re
import time
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

import requests

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────
FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191/v1")

SOURCES = [
    {
        "nom":           "Crunchyscan",
        "url":           "https://crunchyscan.fr",
        "type":          "crunchyscan",
        "sitemap_count": 4,
    },
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
DELAY       = 2.0    # pause entre requêtes (FlareSolverr est plus lent)
MAX_PAGES   = 8
PER_PAGE    = 36
FS_TIMEOUT  = 90     # secondes pour FlareSolverr (résolution du challenge)
HTTP_TIMEOUT = 20

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
}

# Cache de session FlareSolverr par domaine (réutilise les cookies)
_fs_sessions = {}


# ──────────────────────────────────────────────────────────────
# HTTP via FlareSolverr + fallback direct
# ──────────────────────────────────────────────────────────────
def check_flaresolverr():
    """Vérifie que FlareSolverr est disponible."""
    try:
        r = requests.get(FLARESOLVERR_URL.replace("/v1", "/health"), timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def fetch_via_flaresolverr(url, session_id=None):
    """Envoie une requête via FlareSolverr qui résout le challenge Cloudflare."""
    payload = {
        "cmd":        "request.get",
        "url":        url,
        "maxTimeout": 60000,
    }
    if session_id:
        payload["session"] = session_id
    try:
        r = requests.post(FLARESOLVERR_URL, json=payload, timeout=FS_TIMEOUT)
        data = r.json()
        if data.get("status") == "ok":
            html = data["solution"]["response"]
            print(f"    FS✅ {len(html):>7} chars — {url[:65]}")
            return html
        else:
            msg = data.get("message", "unknown")
            print(f"    FS❌ {msg[:80]} — {url[:50]}")
    except Exception as e:
        print(f"    FS⚠ {e} — {url[:50]}")
    return None


def fetch_direct(url):
    """Requête directe sans FlareSolverr (fallback)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, allow_redirects=True)
        print(f"    DR {r.status_code}  {len(r.text):>7} chars — {url[:65]}")
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"    DR⚠ {e} — {url[:50]}")
    return None


_fs_available = None

def fetch(url, retries=2):
    """
    Fetch URL: essaie FlareSolverr d'abord, puis fallback direct.
    Retourne le HTML (str) ou None.
    """
    global _fs_available
    if _fs_available is None:
        _fs_available = check_flaresolverr()
        print(f"  FlareSolverr disponible: {'✅ oui' if _fs_available else '❌ non (fallback direct)'}")

    # Session par domaine pour réutiliser les cookies Cloudflare
    domain = urlparse(url).netloc
    session_id = f"scan_{domain.replace('.', '_')}"

    for attempt in range(retries):
        if _fs_available:
            html = fetch_via_flaresolverr(url, session_id)
            if html:
                return html
        # Fallback direct
        html = fetch_direct(url)
        if html:
            return html
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
        ("&laquo;","«"),("&raquo;","»"),
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
    return re.sub(r"\b(\w)", lambda m: m.group(1).upper(), slug.replace("-", " "))


# ──────────────────────────────────────────────────────────────
# Scraper Crunchyscan — via sitemaps XML (mode rapide)
# ──────────────────────────────────────────────────────────────
def scrape_source_crunchyscan(source):
    """
    Lit les 4 sitemaps XML de Crunchyscan pour récupérer tous les slugs.
    Construit les items sans fetcher les pages détail :
    - titre dérivé du slug
    - cover URL déterministe: /upload/manga/{slug}/cover.jpg
    → ~1800+ séries, rapide et robuste.
    """
    base  = source["url"]
    n     = source.get("sitemap_count", 4)
    items = []
    seen  = set()

    print(f"\n🌐 [Crunchyscan] Lecture sitemaps XML ({n} fichiers)…")
    for i in range(1, n + 1):
        url = f"{base}/sitemap-series-{i}.xml"
        print(f"  🗺  sitemap-series-{i}.xml")
        xml = fetch(url)
        if not xml:
            print(f"    ⚠ inaccessible")
            time.sleep(DELAY)
            continue

        slugs = re.findall(r'/lecture-en-ligne/([^<\s"\']+)', xml)
        print(f"    → {len(slugs)} slugs trouvés")

        for slug in slugs:
            slug = slug.strip("/")
            if not slug or slug in seen:
                continue
            seen.add(slug)
            items.append({
                "id":              slug,
                "titre":           title_from_slug(slug),
                "url":             f"{base}/lecture-en-ligne/{slug}",
                "cover":           f"{base}/upload/manga/{slug}/cover.jpg",
                "type":            "manhwa",
                "statut":          "en cours",
                "synopsis":        "",
                "genres":          [],
                "auteur":          "",
                "note":            0.0,
                "dernierChapitre": 0,
                "sourceNom":       source["nom"],
                "sourceUrl":       source["url"],
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

    items, seen = [], set()

    # Pattern h3.h5 → /manga/
    for href, titre in re.findall(
        r'<h3[^>]*class=["\'][^"\']*h5[^"\']*["\'][^>]*>\s*<a\s+href=["\']([^"\']+/manga/[^"\']+)["\'][^>]*>([^<]+)</a>',
        html, re.I | re.S
    ):
        href  = href.strip()
        titre = clean_text(titre)
        if not titre or href in seen:
            continue
        seen.add(href)

        idx    = html.find(href)
        nearby = html[max(0, idx-800):idx+200]
        nl     = nearby.lower()

        cover = ""
        for attr in ("data-src", "src"):
            m = re.search(rf'{attr}=["\']([^"\']+\.(?:jpg|png|webp)[^"\']*)["\']', nearby, re.I)
            if m:
                cover = m.group(1); break

        type_str = "manhwa"
        for t in ("manhwa","manhua","webtoon","manga"):
            if t in nl: type_str = t; break

        statut = "en cours"
        if any(k in nl for k in ("terminé","completed","finished")): statut = "terminé"
        elif any(k in nl for k in ("pause","hiatus")): statut = "pause"

        items.append({"titre":titre,"url":href,"cover":cover,"type":type_str,"statut":statut})

    # Fallback général
    if not items:
        for href, titre in re.findall(
            r'href=["\']([^"\']+/manga/[^"\']+)["\'][^>]*>\s*(?:<[^>]+>)*\s*([A-ZÀ-Ü][^<]{2,80})',
            html, re.I|re.S
        ):
            titre = clean_text(strip_tags(titre))
            if len(titre)<2 or href in seen: continue
            seen.add(href)
            items.append({"titre":titre,"url":href.strip(),"cover":"","type":"manhwa","statut":"en cours"})

    print(f"    → {len(items)} œuvres")
    return items


def scrape_madara_detail(item):
    html = fetch(item["url"])
    if not html:
        return item

    synopsis = ""
    m = re.search(r'class=["\'][^"\']*summary__content[^"\']*["\'][^>]*>(.*?)</div>', html, re.S|re.I)
    if m: synopsis = clean_text(strip_tags(m.group(1)))[:600]

    genres = list(dict.fromkeys(
        g.lower().replace("-"," ")
        for g in re.findall(r'/genre/([^/"]+)/', html, re.I)
    ))[:6]

    auteur = ""
    m = re.search(r'class=["\'][^"\']*author-content[^"\']*["\'][^>]*>(.*?)</div>', html, re.S|re.I)
    if m: auteur = clean_text(strip_tags(m.group(1)))

    note = 0.0
    m = re.search(r'class=["\'][^"\']*total-votes[^"\']*["\'][^>]*>([0-9.]+)<', html, re.I)
    if not m: m = re.search(r'"ratingValue"\s*:\s*"?([0-9.]+)"?', html)
    if m:
        try:
            raw = float(m.group(1))
            note = round(raw/2,1) if raw>5 else round(raw,1)
        except ValueError: pass

    ch_nums = re.findall(r'/chapter-?(\d+(?:\.\d+)?)', html, re.I)
    dernier_ch = 0
    if ch_nums:
        try: dernier_ch = int(float(max(ch_nums, key=lambda x: float(x))))
        except: pass

    cover = item.get("cover","")
    m = re.search(r'class=["\'][^"\']*summary_image[^"\']*["\'][^>]*>.*?<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']', html, re.S|re.I)
    if m: cover = m.group(1).strip()

    type_str = item.get("type","manhwa")
    hl = html.lower()
    for t in ("manhwa","manhua","webtoon","manga"):
        if t in hl: type_str=t; break

    statut = item.get("statut","en cours")
    if any(k in hl for k in ("terminé","completed","finished")): statut="terminé"
    elif any(k in hl for k in ("pause","hiatus")): statut="pause"

    print(f"    📖 {item['titre'][:45]} Ch.{dernier_ch}")
    return {**item,"cover":cover,"synopsis":synopsis,"genres":genres,
            "auteur":auteur,"type":type_str,"statut":statut,
            "note":note,"dernierChapitre":dernier_ch}


def scrape_source_madara(source):
    print(f"\n🌐 [Madara] {source['nom']} ({source['url']})")
    all_items, seen_urls = [], set()

    for page in range(1, MAX_PAGES+1):
        items = scrape_madara_list(source["url"], page)
        if not items:
            print(f"  ✅ Fin à page {page}")
            break
        new_items = [i for i in items if i["url"] not in seen_urls]
        if not new_items: break
        for i in new_items: seen_urls.add(i["url"])

        for item in new_items[:PER_PAGE]:
            time.sleep(DELAY)
            enriched = scrape_madara_detail(item)
            enriched.update({"sourceNom":source["nom"],"sourceUrl":source["url"],"id":slug_from_url(enriched["url"])})
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
        return []
    except Exception as e:
        import traceback
        print(f"  ❌ Erreur fatale {source['nom']}: {e}")
        traceback.print_exc()
        return []


# ──────────────────────────────────────────────────────────────
# Catalogue
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
    print(f"   FlareSolverr: {FLARESOLVERR_URL}")
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


if __name__ == "__main__":
    main()
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 