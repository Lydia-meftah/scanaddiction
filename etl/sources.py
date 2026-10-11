"""
Extracteurs par source. Chacun renvoie une liste de dossiers 'series' bruts
(déjà au format du modèle, mais non encore normalisés/validés).
Tolérance aux pannes : géré par le pipeline (chaque source est isolée).

NOTE fiabilité : seule MangaDex (API officielle) est stable. Les sites
protégés par Cloudflare (Sushiscan, Raijin, Crunchyscan) peuvent renvoyer
403 depuis une IP datacenter (runner CI) — ils sont donc best-effort.
"""
import re
import time
import logging

from . import config, http_client
from .models import clean, title_from_slug

log = logging.getLogger("etl.sources")

# ── MangaDex (API officielle) ───────────────────────────────────────────────
MDX_BASE = "https://api.mangadex.org"
MDX_STATUT = {"ongoing": "en cours", "completed": "terminé", "hiatus": "pause", "cancelled": "annulé"}
MDX_TYPE = {"manga": "manga", "manhwa": "manhwa", "manhua": "manhua", "doujinshi": "manga", "one_shot": "manga"}


def _mdx_cover(mid, rels):
    for rel in rels or []:
        if rel.get("type") == "cover_art":
            fn = (rel.get("attributes") or {}).get("fileName", "")
            if fn:
                return f"https://uploads.mangadex.org/covers/{mid}/{fn}.512.jpg"
    return ""


def _mdx_title(attrs):
    t = attrs.get("title") or {}
    for lang in ("fr", "en", "ja-ro", "ja"):
        if t.get(lang):
            return t[lang]
    for d in attrs.get("altTitles") or []:
        for lang in ("fr", "en"):
            if d.get(lang):
                return d[lang]
    return next(iter(t.values()), "Sans titre")


def _mdx_author(rels):
    for rel in rels or []:
        if rel.get("type") in ("author", "artist"):
            n = (rel.get("attributes") or {}).get("name", "")
            if n:
                return n
    return ""


def _mdx_genres(attrs):
    return [
        (t.get("attributes", {}).get("name", {}).get("fr")
         or t.get("attributes", {}).get("name", {}).get("en", ""))
        for t in attrs.get("tags") or []
        if t.get("attributes", {}).get("group") == "genre"
    ][:6]


def _mdx_map(m):
    attrs = m.get("attributes") or {}
    mid = m["id"]
    rels = m.get("relationships") or []
    desc = attrs.get("description") or {}
    lang = attrs.get("originalLanguage", "")
    typ = MDX_TYPE.get(lang, "manga") if lang in MDX_TYPE else ("manhwa" if lang == "ko" else "manga")
    return {
        "id": f"mdx-{mid}", "source_code": "mangadex", "mangadex_id": mid, "slug": mid,
        "titre": _mdx_title(attrs), "url": f"https://mangadex.org/title/{mid}",
        "cover": _mdx_cover(mid, rels), "type": typ,
        "statut": MDX_STATUT.get(attrs.get("status", ""), "en cours"),
        "synopsis": clean(desc.get("fr") or desc.get("en") or "")[:600],
        "genres": _mdx_genres(attrs), "auteur": _mdx_author(rels),
        "lecteur_integre": True,
    }


def mangadex(session):
    out, seen = [], set()
    for offset in range(0, config.MDX_MAX_OFFSET + 1, 100):
        params = [
            ("availableTranslatedLanguage[]", "fr"), ("limit", 100), ("offset", offset),
            ("order[followedCount]", "desc"), ("includes[]", "cover_art"),
            ("includes[]", "author"), ("contentRating[]", "safe"), ("contentRating[]", "suggestive"),
        ]
        r = http_client.get(session, f"{MDX_BASE}/manga", params=params)
        data = (r.json().get("data", []) if r else [])
        if not data:
            break
        for m in data:
            if m["id"] not in seen:
                seen.add(m["id"])
                out.append(_mdx_map(m))
        log.info("MangaDex offset %s → cumul %s", offset, len(out))
        time.sleep(config.DELAY)
    return out


# ── Crunchyscan (sitemaps) ──────────────────────────────────────────────────
def crunchyscan(session):
    base = "https://crunchyscan.fr"
    out, seen = [], set()
    for i in range(1, config.CRUNCHYSCAN_MAPS + 1):
        r = http_client.get(session, f"{base}/sitemap-series-{i}.xml")
        if not r:
            continue
        for slug in re.findall(r'/lecture-en-ligne/([^<\s"\'/?]+)', r.text):
            slug = slug.strip("/")
            if slug and slug not in seen:
                seen.add(slug)
                out.append({
                    "id": f"cs-{slug}", "source_code": "crunchyscan", "slug": slug,
                    "titre": title_from_slug(slug), "url": f"{base}/lecture-en-ligne/{slug}",
                    "cover": f"{base}/upload/manga/{slug}/cover.jpg", "type": "manhwa",
                    "statut": "en cours", "lecteur_integre": False,
                })
        time.sleep(config.DELAY)
    return out


# ── Sushiscan (sitemaps WordPress) ──────────────────────────────────────────
def sushiscan(session):
    base = "https://sushiscan.net"
    out, seen = [], set()
    for i in range(1, config.SUSHISCAN_MAPS + 1):
        r = http_client.get(session, f"{base}/wp-sitemap-posts-manga-{i}.xml")
        if not r:
            continue
        for slug in re.findall(r'https?://sushiscan\.net/catalogue/([^/<\s"\']+)/', r.text):
            slug = slug.strip("/")
            if slug and slug not in seen:
                seen.add(slug)
                out.append({
                    "id": f"ss-{slug}", "source_code": "sushiscan", "slug": slug,
                    "titre": title_from_slug(slug), "url": f"{base}/catalogue/{slug}/",
                    "type": "manga", "statut": "en cours", "lecteur_integre": False,
                })
        time.sleep(config.DELAY)
    return out


# ── Raijin-Scans (sitemaps chapitres → slugs séries) ────────────────────────
def raijin(session):
    base = "https://raijin-scans.fr"
    out, seen = [], set()
    for i in range(1, config.RAIJIN_MAPS + 1):
        r = http_client.get(session, f"{base}/wp-sitemap-posts-wp-manga-{i}.xml")
        if not r:
            break
        for slug in re.findall(r'raijin-scans\.fr/manga/([^/<\s"\']+)/\d+/', r.text):
            if slug and slug not in seen:
                seen.add(slug)
                out.append({
                    "id": f"rj-{slug}", "source_code": "raijin", "slug": slug,
                    "titre": title_from_slug(slug), "url": f"{base}/manga/{slug}/",
                    "type": "manhwa", "statut": "en cours", "lecteur_integre": False,
                })
        time.sleep(config.DELAY)
    return out


# ── Scan-Manga (pages SSR + meta OG) ────────────────────────────────────────
SM_BASE = "https://www.scan-manga.com"
SM_TYPE_MAP = {"manga": "manga", "manhwa": "manhwa", "manhua": "manhua", "bd": "manga", "novel": "manga", "webtoon": "manhwa"}
SM_DEMO = {"shonen": "Shonen", "seinen": "Seinen", "shojo": "Shojo", "josei": "Josei", "isekai": "Isekai", "ecchi": "Ecchi"}


def _sm_detail(html, url):
    m = (re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I)
         or re.search(r'content=["\']([^"\']+)["\'][^>]+property=["\']og:image', html, re.I))
    cover = m.group(1).strip() if m else ""
    m = (re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.I)
         or re.search(r'<title>([^<]+)</title>', html, re.I))
    raw = m.group(1).strip() if m else ""
    titre = re.sub(r'\s+VF\s*[-–].*$', '', re.sub(r'^Lire\s+', '', raw, flags=re.I), flags=re.I).strip()
    m = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.I)
    desc = (m.group(1) if m else "").lower()
    type_str = next((SM_TYPE_MAP[k] for k in ("manhwa", "manhua", "webtoon", "bd", "novel", "manga") if k in desc), "manga")
    genres = [lab for kw, lab in SM_DEMO.items() if kw in desc][:3]
    am = re.search(r'\(\d{4}\s*[-–]\s*([^)]+)\)', desc) or re.search(r'\(([^)]{3,40})\)\s*$', desc)
    idm = re.search(r'/(\d+(?:-\d+)?)/[^/]+\.html', url)
    sid = idm.group(1) if idm else re.sub(r'[^\w]', '-', url)
    return {
        "id": f"sm-{sid}", "source_code": "scan-manga", "slug": sid,
        "titre": clean(titre) or url.split('/')[-1].replace('.html', '').replace('-', ' ').title(),
        "url": url, "cover": cover, "type": type_str, "statut": "en cours",
        "genres": genres, "auteur": (am.group(1).strip() if am else ""), "lecteur_integre": False,
    }


def scan_manga(session):
    r = http_client.get(session, f"{SM_BASE}/scanlation/En-cours.html")
    if not r:
        return []
    pat = r'href=["\'](?:https?://www\.scan-manga\.com)?(/\d+(?:-\d+)?/[A-Za-z0-9][^"\'<>\s]+\.html)'
    hrefs = list(dict.fromkeys(re.findall(pat, r.text)))[: config.SM_MAX_SERIES]
    out = []
    for href in hrefs:
        url = SM_BASE + href
        d = http_client.get(session, url)
        if d:
            item = _sm_detail(d.text, url)
            if item["titre"]:
                out.append(item)
        time.sleep(config.DELAY)
    return out


# Registre : (code, fonction). L'ordre définit la priorité de dédup.
REGISTRY = [
    ("mangadex", mangadex),
    ("crunchyscan", crunchyscan),
    ("scan-manga", scan_manga),
    ("sushiscan", sushiscan),
    ("raijin", raijin),
]
