"""Normalisation et validation du modèle 'series' (contrat de données)."""
import re
from . import config


def clean(txt: str) -> str:
    if not txt:
        return ""
    txt = re.sub(r"<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def title_from_slug(slug: str) -> str:
    return re.sub(r"\b(\w)", lambda m: m.group(1).upper(), slug.replace("-", " "))


def normalize(rec: dict) -> dict:
    """Applique valeurs par défaut et bornes au dossier d'une série."""
    rec.setdefault("mangadex_id", None)
    rec.setdefault("slug", None)
    rec["cover"] = rec.get("cover") or ""
    rec["synopsis"] = clean(rec.get("synopsis", ""))[:600]
    rec["auteur"] = rec.get("auteur") or ""
    rec["genres"] = rec.get("genres") or []
    rec["note"] = float(rec.get("note") or 0)
    rec["dernier_chapitre"] = float(rec.get("dernier_chapitre") or 0)
    rec["lecteur_integre"] = 1 if rec.get("lecteur_integre") else 0
    if rec.get("type") not in config.VALID_TYPES:
        rec["type"] = "manga"
    if rec.get("statut") not in config.VALID_STATUTS:
        rec["statut"] = "en cours"
    rec["titre"] = clean(rec.get("titre", ""))
    return rec


def validate(records: list[dict]) -> tuple[list[dict], list[str]]:
    """Déduplique par id, vérifie champs requis + enums. Renvoie (valides, erreurs)."""
    errors, seen, valid = [], set(), []
    for i, r in enumerate(records):
        missing = [f for f in config.REQUIRED_FIELDS if not r.get(f)]
        if missing:
            errors.append(f"#{i} ({r.get('id','?')}) champs manquants: {missing}")
            continue
        if r["type"] not in config.VALID_TYPES:
            errors.append(f"{r['id']} type invalide: {r['type']}")
            continue
        if r["statut"] not in config.VALID_STATUTS:
            errors.append(f"{r['id']} statut invalide: {r['statut']}")
            continue
        if r["id"] in seen:
            continue  # doublon silencieux
        seen.add(r["id"])
        valid.append(r)
    return valid, errors
