#!/usr/bin/env python3
"""
scraper.py — Catalogue francophone scantrad
Récupère les manhwa/webtoon/manga de sites scantrad francophones
et génère data/catalogue-fr.json

Sources supportées :
  - raijin-scans.fr     (WordPress/Madara theme)
  - sushiscan.net       (WordPress/Madara theme)
  - manga-scantrad.io   (WordPress/Madara theme)
  - phenixscans.fr      (WordPress/Madara theme)
  - crunchyscan.fr      (plateforme custom, via sitemaps XML)

Usage : python scraper.py
"""

import json
import re
import time
import os
import gzip as gzip_module
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.parse import urljoin, urlparse, unquote
from html.parser import HTMLParser

# ──────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────
SOURCES = [
    # ── Sites WordPress / Madara theme ────────────────────────
    {
        "nom": "Raijin Scans",
        "url": "https://raijin-scans.fr",
        "type": "madara",
        "langue": "fr",
    },
    {
        "nom": "Sushiscan",
        "url": "https://sushiscan.net",
        "type": "madara",
        "langue": "fr",
    },
    {
        "nom": "Manga Scantrad",
        "url": "https://manga-scantrad.io",
        "type": "madara",
        "langue": "fr",
    },
    {
        "nom": "Phénix Scans",
        "url": "https://www.phenixscans.fr",
        "type": "madara",
        "langue": "fr",
    },
    # ── Plateformes custom ────────────────────────────────────
    {
        "nom": "Crunchyscan",
        "url": "https://crunchyscan.fr",
        "type": "crunchyscan",
        "langue": "fr",
        # 4 sitemaps XML listant toutes les séries
        "sitemap_count": 4,
        # Limite de pages détail à fetcher (pour rester < 20 min)
        "max_detail": 400,
    },
]

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "catalogue-fr.json")
DELAY       = 1.5    # secondes entre requêtes (respectueux du serveur)
DELAY_CS    = 0.8    # délai pour Crunchyscan detail pages (SSR léger)
MAX_PAGES   = 10     # pages de liste max par source Madara
PER_PAGE    = 36     # items par page Madara
TIMEOUT     = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
    # Pas de Accept-Encoding: urllib ne décompresse pas le gzip automatiquement
    # On gère manuellement via Content-Encoding dans fetch()
}


# ──────────────────────────────────────────────────────────────
# Utilitaires HTTP / parsing
# ──────────────────────────────────────────────────────────────
def fetch(url, retries=3):
    """Fetch URL, retourne le HTML (str) ou None."""
    for attempt in range(retries):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()

                # Décompression manuelle si le serveur renvoie du gzip
                encoding = r.headers.get("Content-Encoding", "")
                if "gzip" in encoding:
                    try:
                        raw = gzip_module.decompress(raw)
                    except Exception:
                        pass

                charset = "utf-8"
                ct = r.headers.get("Content-Type", "")
                m = re.search(r"charset=([^\s;]+)", ct, re.I)
                if m:
                    charset = m.group(1).lower().replace("iso-8859-1", "latin-1")
                try:
                    return raw.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    return raw.decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  ⚠ fetch({url}) tentative {attempt+1}: {e}")
            if attempt < retries - 1:
                time.sleep(2)
    return None


def extract_attr(html, tag, attr, class_hint=None):
    """Extrait la valeur d'un attribut depuis le premier tag correspondant."""
    if class_hint:
        for pattern in [
            rf'<{tag}[^>]*class=["\'][^"\']*{re.escape(class_hint)}[^"\']*["\'][^>]*{attr}=["\']([^"\']+)["\']',
            rf'<{tag}[^>]*{attr}=["\']([^"\']+)["\'][^>]*class=["\'][^"\']*{re.escape(class_hint)}[^"\']*["\']',
        ]:
            m = re.search(pattern, html, re.I | re.S)
            if m:
                return m.group(1).strip()
        return None
    m = re.search(rf'<{tag}[^>]*\s{attr}=["\']([^"\']+)["\']', html, re.I)
    return m.group(1).strip() if m else None


def strip_tags(html):
    return re.sub(r"<[^>]+>", "", html).strip()


def clean_text(s):
    if not s:
        return ""
    for old, new in [
        ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&#039;", "'"), ("&rsquo;", "'"),
        ("&nbsp;", " "), ("\xa0", " "), ("&laquo;", "«"), ("&raquo;", "»"),
    ]:
        s = s.replace(old, new)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def slug_from_url(url):
    m = re.search(r"/manga/([^/?#]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/lecture-en-ligne/([^/?#]+)", url)
    if m:
        return m.group(1)
    return urlparse(url).path.strip("/").replace("/", "-")


def title_from_slug(slug):
    """Génère un titre lisible depuis un slug (fallback)."""
    return slug.replace("-", " ").title()


# ──────────────────────────────────────────────────────────────
# Scraper Madara (WordPress theme commun)
# ──────────────────────────────────────────────────────────────
def scrape_madara_list(base_url, page=1):
    """
    Récupère une page de liste depuis un site Madara.
    Essaie plusieurs patterns d'URL selon le site.
    """
    # Pattern 1: recherche post_type wp-manga
    url = f"{base_url}/page/{page}/?post_type=wp-manga&s=&sort=recently_added"
    print(f"  📄 Liste page {page}: {url}")
    html = fetch(url)
    if not html:
        return []

    items = []
    seen = set()

    # Pattern h3.h5 → lien /manga/
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
        nearby = html[max(0, idx - 800):idx + 200]

        cover = (extract_attr(nearby, "img", "data-src") or
                 extract_attr(nearby, "img", "src") or "")

        nearby_lower = nearby.lower()
        type_str = "manhwa"
        for t in ("manhwa", "manhua", "webtoon", "manga"):
            if t in nearby_lower:
                type_str = t
                break

        statut = "en cours"
        if any(k in nearby_lower for k in ("terminé", "completed", "finished")):
            statut = "terminé"
        elif any(k in nearby_lower for k in ("pause", "hiatus")):
            statut = "pause"

        items.append({"titre": titre, "url": href, "cover": cover,
                      "type": type_str, "statut": statut})

    # Fallback: tout lien /manga/
    if not items:
        all_links = re.findall(
            r'href=["\']([^"\']+/manga/[^"\']+)["\'][^>]*>\s*(?:<[^>]+>)*\s*([A-ZÀ-Ü][^<]{2,80})',
            html, re.I | re.S
        )
        for href, titre in all_links:
            titre = clean_text(strip_tags(titre))
            if len(titre) < 2 or href in seen:
                continue
            seen.add(href)
            items.append({"titre": titre, "url": href.strip(),
                          "cover": "", "type": "manhwa", "statut": "en cours"})

    print(f"    → {len(items)} œuvres trouvées")
    return items


def scrape_madara_detail(item):
    """Enrichit un item avec synopsis, genres, auteur, note, dernier chapitre."""
    html = fetch(item["url"])
    if not html:
        return item

    # Synopsis
    synopsis = ""
    m = re.search(
        r'class=["\'][^"\']*summary__content[^"\']*["\'][^>]*>(.*?)</div>',
        html, re.S | re.I
    )
    if m:
        synopsis = clean_text(strip_tags(m.group(1)))[:600]

    # Genres
    genres = re.findall(r'/genre/([^/"]+)/', html, re.I)
    genres = list(dict.fromkeys(g.lower().replace("-", " ") for g in genres))[:6]

    # Auteur
    auteur = ""
    m = re.search(r'class=["\'][^"\']*author-content[^"\']*["\'][^>]*>(.*?)</div>',
                  html, re.S | re.I)
    if m:
        auteur = clean_text(strip_tags(m.group(1)))

    # Note
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

    # Dernier chapitre
    ch_nums = re.findall(r'/chapter-?(\d+(?:\.\d+)?)', html, re.I)
    if not ch_nums:
        ch_nums = re.findall(r'Ch\.\s*(\d+(?:\.\d+)?)', html, re.I)
    dernier_ch = 0
    if ch_nums:
        try:
            dernier_ch = int(float(max(ch_nums, key=lambda x: float(x))))
        except (ValueError, TypeError):
            pass

    # Cover haute résolution
    cover = item.get("cover", "")
    m = re.search(
        r'class=["\'][^"\']*summary_image[^"\']*["\'][^>]*>.*?<img[^>]+(?:src|data-src)=["\']([^"\']+)["\']',
        html, re.S | re.I
    )
    if m:
        cover = m.group(1).strip()

    # Type précis depuis la page détail
    type_str = item.get("type", "manhwa")
    hl = html.lower()
    for label in ("manhwa", "manhua", "webtoon", "manga"):
        if label in hl:
            type_str = label
            break

    # Statut précis
    statut = item.get("statut", "en cours")
    if any(k in hl for k in ("terminé", "completed", "finished")):
        statut = "terminé"
    elif any(k in hl for k in ("pause", "hiatus")):
        statut = "pause"

    print(f"  📖 {item['titre'][:50]} — Ch.{dernier_ch}")
    return {
        **item,
        "cover": cover, "synopsis": synopsis, "genres": genres,
        "auteur": auteur, "type": type_str, "statut": statut,
        "note": note, "dernierChapitre": dernier_ch,
    }


def scrape_source_madara(source):
    """Scrape un site Madara complet."""
    print(f"\n🌐 [Madara] Scraping: {source['nom']} ({source['url']})")
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
            enriched["id"] = slug_from_url(enriched["url"])
            all_items.append(enriched)

        time.sleep(DELAY)

    print(f"  → Total: {len(all_items)} œuvres pour {source['nom']}")
    return all_items


# ──────────────────────────────────────────────────────────────
# Scraper Crunchyscan (plateforme custom — via sitemaps XML)
# ──────────────────────────────────────────────────────────────
def scrape_crunchyscan_sitemaps(source):
    """
    Récupère tous les slugs depuis sitemap-series-1.xml … sitemap-series-N.xml.
    Retourne une liste de slugs dédupliqués.
    """
    base = source["url"]
    n    = source.get("sitemap_count", 4)
    slugs = []
    seen  = set()

    for i in range(1, n + 1):
        url = f"{base}/sitemap-series-{i}.xml"
        print(f"  🗺  Sitemap {i}: {url}")
        xml = fetch(url)
        if not xml:
            continue
        found = re.findall(r'/lecture-en-ligne/([^<\s"\']+)', xml)
        for s in found:
            s = s.strip("/")
            if s and s not in seen:
                seen.add(s)
                slugs.append(s)
        print(f"    → {len(found)} slugs")
        time.sleep(DELAY)

    return slugs


def parse_crunchyscan_detail(html, slug, source):
    """
    Parse la page détail d'une série Crunchyscan (SSR).
    Extrait titre, type, genres, synopsis, cover, chapitre, statut.
    """
    base = source["url"]

    # ── Titre ──────────────────────────────────────────────────
    titre = ""
    # og:title
    m = re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\'|]+)["\']', html, re.I)
    if not m:
        m = re.search(r'content=["\']([^"\'|]+)["\'][^>]*property=["\']og:title["\']', html, re.I)
    if m:
        titre = clean_text(m.group(1).split("|")[0].split(" — ")[0])
    if not titre:
        m = re.search(r'<title>([^<|—]+)', html)
        if m:
            titre = clean_text(m.group(1))
    if not titre:
        titre = title_from_slug(slug)

    # ── Type ───────────────────────────────────────────────────
    # Pattern meta description: "…un MANHWA en scan VF/FR…"
    type_str = "manhwa"
    m = re.search(
        r'un\s+(manhwa|manhua|manga|webtoon|bd|one[- ]shot)[^<]{0,30}en scan',
        html, re.I
    )
    if m:
        raw_type = m.group(1).lower()
        type_str = {"bd": "manga", "one shot": "manga", "one-shot": "manga"}.get(raw_type, raw_type)

    # ── Genres ─────────────────────────────────────────────────
    genres = []
    m = re.search(r'genres comme ([^.!<"]{3,200})', html, re.I)
    if m:
        genres_raw = m.group(1)
        genres = [g.strip().lower() for g in re.split(r'[,&]', genres_raw) if g.strip()][:6]

    # Fallback: liens /catalog/genre/
    if not genres:
        genre_links = re.findall(r'/catalog/genre/([^/"]+)', html, re.I)
        genres = list(dict.fromkeys(
            g.replace("-", " ").lower() for g in genre_links
            if g not in ("action", "webtoon", "manhwa", "manhua", "manga")  # trop générique comme genres
        ))[:6]
        # si toujours vide, ajouter quand même
        if not genres:
            genres = list(dict.fromkeys(
                g.replace("-", " ").lower() for g in genre_links
            ))[:6]

    # ── Synopsis ───────────────────────────────────────────────
    synopsis = ""
    # Extrait depuis le paramètre "synopsis=" dans l'URL de l'og:image
    og_m = re.search(
        r'(?:property=["\']og:image["\'][^>]+content|content[^>]+property=["\']og:image["\'])[^=]*=["\']([^"\']+)["\']',
        html, re.I
    )
    if og_m:
        syn_m = re.search(r'[?&]synopsis=([^&"\']+)', og_m.group(1), re.I)
        if syn_m:
            try:
                synopsis = unquote(syn_m.group(1))[:600]
                synopsis = clean_text(synopsis)
            except Exception:
                pass

    # ── Cover ──────────────────────────────────────────────────
    # URL déterministe: /upload/manga/{slug}/cover.jpg
    cover = f"{base}/upload/manga/{slug}/cover.jpg"

    # ── Dernier chapitre ───────────────────────────────────────
    ch_nums = re.findall(r'/chapitre-(\d+(?:[.-]\d+)?)', html, re.I)
    dernier_ch = 0
    if ch_nums:
        try:
            dernier_ch = int(float(max(ch_nums, key=lambda x: float(x.replace("-", ".")))))
        except (ValueError, TypeError):
            pass

    # ── Statut ─────────────────────────────────────────────────
    statut = "en cours"
    hl = html.lower()
    if "terminé" in hl or "termine" in hl:
        statut = "terminé"
    elif "abandonné" in hl or "abandonne" in hl:
        statut = "pause"

    return {
        "id":             slug,
        "titre":          titre,
        "url":            f"{base}/lecture-en-ligne/{slug}",
        "cover":          cover,
        "type":           type_str,
        "statut":         statut,
        "synopsis":       synopsis,
        "genres":         genres,
        "auteur":         "",
        "note":           0.0,
        "dernierChapitre": dernier_ch,
        "sourceNom":      source["nom"],
        "sourceUrl":      source["url"],
    }


def scrape_source_crunchyscan(source):
    """Scrape Crunchyscan via sitemaps XML + pages détail SSR."""
    print(f"\n🌐 [Crunchyscan] Scraping: {source['nom']} ({source['url']})")

    # 1. Récupérer tous les slugs depuis les sitemaps
    slugs = scrape_crunchyscan_sitemaps(source)
    print(f"  📋 {len(slugs)} séries uniques dans les sitemaps")

    max_detail = source.get("max_detail", 400)
    slugs_to_fetch = slugs[:max_detail]
    if len(slugs) > max_detail:
        print(f"  ℹ️  Limité à {max_detail} séries (sur {len(slugs)}) pour respecter le temps d'exécution")

    # 2. Fetcher les pages détail
    items = []
    base = source["url"]
    for idx, slug in enumerate(slugs_to_fetch, 1):
        url  = f"{base}/lecture-en-ligne/{slug}"
        html = fetch(url)
        if not html:
            # Construire un item minimal depuis le slug
            items.append({
                "id": slug, "titre": title_from_slug(slug),
                "url": url, "cover": f"{base}/upload/manga/{slug}/cover.jpg",
                "type": "manhwa", "statut": "en cours", "synopsis": "",
                "genres": [], "auteur": "", "note": 0.0, "dernierChapitre": 0,
                "sourceNom": source["nom"], "sourceUrl": source["url"],
            })
            continue

        item = parse_crunchyscan_detail(html, slug, source)
        items.append(item)
        if idx % 50 == 0:
            print(f"  ⏳ {idx}/{len(slugs_to_fetch)} séries traitées…")
        time.sleep(DELAY_CS)

    print(f"  → Total: {len(items)} œuvres pour {source['nom']}")
    return items


# ──────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────
def scrape_source(source):
    """Dispatch vers le bon scraper selon le type de source."""
    try:
        if source["type"] == "madara":
            return scrape_source_madara(source)
        elif source["type"] == "crunchyscan":
            return scrape_source_crunchyscan(source)
        else:
            print(f"  ⚠ Type de source inconnu: {source['type']}")
            return []
    except Exception as e:
        print(f"  ❌ Erreur fatale pour {source['nom']}: {e}")
        import traceback
        traceback.print_exc()
        return []


# ──────────────────────────────────────────────────────────────
# Construction du catalogue final
# ──────────────────────────────────────────────────────────────
def build_catalogue(all_items):
    """Construit le JSON final, dédupliqué et trié."""
    # Déduplique par titre normalisé (garde la première occurrence)
    seen_titres = {}
    unique = []
    for item in all_items:
        key = re.sub(r"[^a-z0-9]", "", item["titre"].lower())
        if key and key not in seen_titres:
            seen_titres[key] = True
            unique.append(item)

    # Tri alphabétique
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
        print(f"  📦 Cumul: {len(all_items)} œuvres au total\n")

    catalogue = build_catalogue(all_items)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogue, f, 