#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chapters.py — Scanaddiction · Extraction de la liste des chapitres d'une série
================================================================================

Donne-lui l'URL d'une série (page de l'œuvre) et il te sort TOUS ses chapitres
— numéro, titre, URL, date — dans un tableau, exportable en JSON et/ou Excel.

But : centraliser le repérage des chapitres pour l'outil de trad. La sortie JSON
est pensée pour alimenter l'« Agent · lien » (une liste d'URLs prête à enfiler).

Architecture multi-sites à parsers DÉDIÉS (comme scraper.py) :
    - un REGISTRY qui associe un domaine à un parser,
    - chaque parser expose matches(url) + list_chapters(url),
    - la logique de PARSING est séparée de l'I/O réseau → réutilisable tel quel
      dans une Cloudflare Function (functions/api) plus tard.

Parsers inclus :
    - Coffeemanga         ✅ vérifié sur le vrai site (site custom Tailwind, paginé)
    - Madara (générique)  ⚠️ à valider au 1er run réel — couvre Sushiscan, Raijin,
                             et la majorité des sites de scans EN (thème WordPress Madara)
    - MangaDex            ✅ API officielle (même source que scraper.py), chapitres FR

Ajouter un site = écrire une classe Parser + l'ajouter à REGISTRY. Rien d'autre.

--------------------------------------------------------------------------------
Usage CLI
    python chapters.py "https://coffeemanga.net/manga/<slug>/"
    python chapters.py "<url>" --json chapitres.json --xlsx chapitres.xlsx
    python chapters.py "<url>" --json -            # JSON sur la sortie standard
    python chapters.py "<url>" --lang fr           # langue (MangaDex surtout)
    python chapters.py "<url>" --asc               # tri croissant (défaut : décroissant)

Dépendances : requests, beautifulsoup4, openpyxl (déjà présentes dans ton env).
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None


# ══════════════════════════════════════════════════════════════════════════
# Config HTTP
# ══════════════════════════════════════════════════════════════════════════
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
HTTP_TIMEOUT = 30
DELAY = 0.8            # pause entre deux pages d'un même site (politesse)
MAX_PAGES = 200       # garde-fou anti-boucle sur la pagination


def http_get(session: requests.Session, url: str, **kw) -> requests.Response | None:
    for attempt in (1, 2):
        try:
            r = session.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, **kw)
            if r.status_code == 200:
                return r
            if r.status_code == 429:
                time.sleep(5 * attempt)
                continue
            sys.stderr.write(f"  HTTP {r.status_code} — {url}\n")
            return None
        except requests.RequestException as e:
            sys.stderr.write(f"  erreur réseau ({attempt}/2) {type(e).__name__} — {url}\n")
            time.sleep(1.5 * attempt)
    return None


def http_post(session: requests.Session, url: str, data=None, **kw) -> requests.Response | None:
    try:
        r = session.post(url, headers=HEADERS, data=data, timeout=HTTP_TIMEOUT, **kw)
        return r if r.status_code == 200 else None
    except requests.RequestException as e:
        sys.stderr.write(f"  POST erreur {type(e).__name__} — {url}\n")
        return None


# ══════════════════════════════════════════════════════════════════════════
# Modèle
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class Chapter:
    numero: str            # "92", "10.5" … tel qu'affiché / tiré de l'URL
    titre: str             # "Chapter 92"
    url: str               # URL absolue du chapitre
    date: str              # date ISO si dispo, sinon texte brut, sinon ""
    source: str = ""       # nom du site

    def sort_key(self) -> float:
        m = re.search(r"-?\d+(?:\.\d+)?", self.numero or "")
        return float(m.group()) if m else -1.0


def _num_from_href(href: str) -> str:
    """Extrait le n° de chapitre depuis une URL (…/chapter-10-5/ → '10.5')."""
    m = re.search(r"chapt(?:er|re)[-_/]([0-9]+(?:[-.][0-9]+)?)", href, re.I)
    if m:
        return m.group(1).replace("-", ".")
    m = re.search(r"/(\d+(?:\.\d+)?)/?$", href.rstrip("/") + "/")
    return m.group(1) if m else ""


# ══════════════════════════════════════════════════════════════════════════
# PARSER 1 — Coffeemanga (✅ vérifié)
#   Site custom Tailwind. Chapitres en <a class="chapter-card">, paginés via
#   /manga/<slug>/chapters/<n>/. Date ISO dans <time datetime=…>.
# ══════════════════════════════════════════════════════════════════════════
class CoffeemangaParser:
    name = "Coffeemanga"
    DOMAINS = ("coffeemanga.net", "coffeemanga.io", "coffeemanga.org")

    @classmethod
    def matches(cls, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host == d or host.endswith("." + d) for d in cls.DOMAINS)

    # --- parsing pur (testable hors-ligne) ---------------------------------
    @staticmethod
    def parse_page(html: str, base_url: str):
        """Retourne (chapitres_de_la_page, numero_de_page_max)."""
        soup = BeautifulSoup(html, "html.parser")
        chapters = []
        for a in soup.select("a.chapter-card"):
            href = a.get("href", "")
            if not href:
                continue
            url = urljoin(base_url, href)
            badge = a.find("span")                       # 1er span = n° affiché
            title_el = a.select_one(".font-semibold")
            time_el = a.find("time")
            numero = _num_from_href(href) or (badge.get_text(strip=True) if badge else "")
            titre = title_el.get_text(strip=True) if title_el else (
                badge.get_text(strip=True) if badge else "")
            date = ""
            if time_el:
                date = time_el.get("datetime") or time_el.get_text(strip=True)
            chapters.append(Chapter(numero, titre, url, date, "Coffeemanga"))

        # pagination : <nav aria-label="Chapter list pages"> … /chapters/<n>/
        max_page = 1
        for a in soup.select('a[href*="/chapters/"]'):
            m = re.search(r"/chapters/(\d+)/?", a.get("href", ""))
            if m:
                max_page = max(max_page, int(m.group(1)))
        return chapters, max_page

    # --- récupération réseau ----------------------------------------------
    @classmethod
    def list_chapters(cls, url: str, session: requests.Session, **_) -> list[Chapter]:
        base = url if url.endswith("/") else url + "/"
        base = re.sub(r"chapters/\d+/?$", "", base)      # normalise si on tombe sur une page de pagination
        r = http_get(session, base)
        if not r:
            return []
        first, max_page = cls.parse_page(r.text, base)
        seen = {c.url: c for c in first}
        pages_done = {1}
        page = 2
        while page <= max_page and len(pages_done) < MAX_PAGES:
            time.sleep(DELAY)
            r = http_get(session, urljoin(base, f"chapters/{page}/"))
            pages_done.add(page)
            if r:
                chs, mp = cls.parse_page(r.text, base)
                for c in chs:
                    seen.setdefault(c.url, c)
                max_page = max(max_page, mp)             # pagination fenêtrée → on élargit
            page += 1
        return list(seen.values())


# ══════════════════════════════════════════════════════════════════════════
# PARSER 2 — Madara générique (⚠️ à valider au 1er run)
#   Thème WordPress ultra répandu. Les chapitres sont souvent chargés en AJAX :
#     POST {serie}ajax/chapters/   → <li class="wp-manga-chapter"> …
#   Fallback : POST /wp-admin/admin-ajax.php (action=manga_get_chapters).
#   Couvre Sushiscan, Raijin-Scans, et des centaines de sites EN.
# ══════════════════════════════════════════════════════════════════════════
class MadaraParser:
    name = "Madara"
    # domaines connus chez toi ; le dispatcher peut aussi l'essayer en dernier recours
    DOMAINS = ("sushiscan.net", "raijin-scans.fr")

    @classmethod
    def matches(cls, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return any(host == d or host.endswith("." + d) for d in cls.DOMAINS)

    @staticmethod
    def parse_list(html: str, base_url: str, source: str = "Madara") -> list[Chapter]:
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for li in soup.select("li.wp-manga-chapter"):
            a = li.find("a")
            if not a or not a.get("href"):
                continue
            url = urljoin(base_url, a["href"])
            titre = a.get_text(strip=True)
            date_el = li.select_one(".chapter-release-date, .chapter-release-date i, span.chapter-release-date")
            date = date_el.get_text(strip=True) if date_el else ""
            out.append(Chapter(_num_from_href(url) or titre, titre, url, date, source))
        return out

    @classmethod
    def list_chapters(cls, url: str, session: requests.Session, **_) -> list[Chapter]:
        base = url if url.endswith("/") else url + "/"
        src = urlparse(base).netloc.replace("www.", "")

        # 1) endpoint Madara récent : {serie}ajax/chapters/
        r = http_post(session, urljoin(base, "ajax/chapters/"))
        if r and "wp-manga-chapter" in r.text:
            return cls.parse_list(r.text, base, src)

        # 2) la liste est parfois déjà dans le HTML de la page
        r = http_get(session, base)
        if r and "wp-manga-chapter" in r.text:
            chs = cls.parse_list(r.text, base, src)
            if chs:
                return chs
            # 3) fallback admin-ajax avec l'id du post
            mid = None
            m = re.search(r'data-id=["\'](\d+)["\']', r.text) or re.search(r'manga_id["\']?\s*[:=]\s*["\']?(\d+)', r.text)
            if m:
                mid = m.group(1)
            if mid:
                ajax = f"{urlparse(base).scheme}://{urlparse(base).netloc}/wp-admin/admin-ajax.php"
                r2 = http_post(session, ajax, data={"action": "manga_get_chapters", "manga": mid})
                if r2 and "wp-manga-chapter" in r2.text:
                    return cls.parse_list(r2.text, base, src)
        return []


# ══════════════════════════════════════════════════════════════════════════
# PARSER 3 — MangaDex (✅ API officielle)
#   URL type : https://mangadex.org/title/<uuid>  → /manga/<uuid>/feed
# ══════════════════════════════════════════════════════════════════════════
class MangaDexParser:
    name = "MangaDex"
    API = "https://api.mangadex.org"

    @classmethod
    def matches(cls, url: str) -> bool:
        return "mangadex.org" in urlparse(url).netloc.lower()

    @classmethod
    def list_chapters(cls, url: str, session: requests.Session, lang: str = "fr", **_) -> list[Chapter]:
        m = re.search(r"/title/([0-9a-f-]{36})", url)
        if not m:
            sys.stderr.write("  MangaDex : UUID introuvable dans l'URL\n")
            return []
        mid = m.group(1)
        out, offset = [], 0
        while True:
            params = [
                ("translatedLanguage[]", lang),
                ("order[chapter]", "asc"),
                ("limit", 500), ("offset", offset),
                ("includes[]", "scanlation_group"),
                ("contentRating[]", "safe"), ("contentRating[]", "suggestive"),
                ("contentRating[]", "erotica"),
            ]
            r = http_get(session, f"{cls.API}/manga/{mid}/feed", params=params)
            if not r:
                break
            data = r.json()
            for ch in data.get("data", []):
                at = ch.get("attributes", {})
                num = at.get("chapter") or "0"
                titre = at.get("title") or f"Chapitre {num}"
                date = at.get("publishAt", "") or at.get("readableAt", "")
                out.append(Chapter(num, titre, f"https://mangadex.org/chapter/{ch['id']}", date, "MangaDex"))
            total = data.get("total", 0)
            offset += 500
            if offset >= total:
                break
            time.sleep(DELAY)
        # dédoublonne les multi-groupes sur un même n° en gardant le 1er
        uniq = {}
        for c in out:
            uniq.setdefault(c.numero, c)
        return list(uniq.values())


# ══════════════════════════════════════════════════════════════════════════
# Dispatcher
# ══════════════════════════════════════════════════════════════════════════
REGISTRY = [CoffeemangaParser, MadaraParser, MangaDexParser]


def get_parser(url: str):
    for p in REGISTRY:
        if p.matches(url):
            return p
    return None


def extract_chapters(url: str, lang: str = "fr", ascending: bool = False) -> dict:
    parser = get_parser(url)
    if parser is None:
        raise ValueError(
            f"Aucun parser pour « {urlparse(url).netloc} ». "
            f"Sites gérés : {', '.join(sum([list(getattr(p,'DOMAINS',(p.name,))) for p in REGISTRY], []))}"
        )
    if BeautifulSoup is None and parser is not MangaDexParser:
        raise RuntimeError("beautifulsoup4 manquant : pip install beautifulsoup4")

    with requests.Session() as s:
        chapters = parser.list_chapters(url, s, lang=lang)

    chapters.sort(key=lambda c: c.sort_key(), reverse=not ascending)
    return {
        "serie_url": url,
        "source": parser.name,
        "extrait_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(chapters),
        "chapitres": [asdict(c) for c in chapters],
    }


# ══════════════════════════════════════════════════════════════════════════
# Exports
# ══════════════════════════════════════════════════════════════════════════
def to_json(result: dict, path: str) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if path == "-":
        sys.stdout.write(text + "\n")
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write(f"  → JSON  : {path}\n")


def to_xlsx(result: dict, path: str) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "Chapitres"
    headers = ["N°", "Titre", "URL", "Date", "Source"]
    ws.append(headers)
    head_fill = PatternFill("solid", fgColor="6D28D9")   # violet Scanaddiction
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = head_fill
        c.alignment = Alignment(vertical="center")
    for ch in result["chapitres"]:
        ws.append([ch["numero"], ch["titre"], ch["url"], ch["date"], ch["source"]])
    # URL cliquables
    for row in range(2, ws.max_row + 1):
        cell = ws.cell(row=row, column=3)
        if cell.value:
            cell.hyperlink = cell.value
            cell.font = Font(color="2563EB", underline="single")
    widths = [8, 40, 70, 26, 14]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:E{ws.max_row}"
    wb.save(path)
    sys.stderr.write(f"  → Excel : {path}\n")


# ══════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Extrait la liste des chapitres d'une série (JSON + Excel).")
    ap.add_argument("url", help="URL de la page de la série")
    ap.add_argument("--json", metavar="FICHIER", help="export JSON ('-' = stdout)")
    ap.add_argument("--xlsx", metavar="FICHIER", help="export Excel .xlsx")
    ap.add_argument("--lang", default="fr", help="langue des chapitres (MangaDex) — défaut fr")
    ap.add_argument("--asc", action="store_true", help="tri croissant (défaut : décroissant)")
    args = ap.parse_args(argv)

    try:
        result = extract_chapters(args.url, lang=args.lang, ascending=args.asc)
    except (ValueError, RuntimeError) as e:
        sys.stderr.write(f"❌ {e}\n")
        return 2

    sys.stderr.write(f"✅ {result['total']} chapitre(s) — source {result['source']}\n")

    # exports demandés ; par défaut, JSON sur stdout si rien n'est précisé
    if not args.json and not args.xlsx:
        to_json(result, "-")
    else:
        if args.json:
            to_json(result, args.json)
        if args.xlsx:
            to_xlsx(result, args.xlsx)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
