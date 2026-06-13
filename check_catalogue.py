#!/usr/bin/env python3
"""
check_catalogue.py - Verification non bloquante du catalogue genere.

Affiche un resume du catalogue. Si moins de 5 oeuvres ont ete trouvees,
emet un avertissement GitHub Actions (::warning::) mais ne fait PAS
echouer le workflow : les sources peuvent etre temporairement
inaccessibles (Cloudflare, DNS, etc.) sans que cela soit une erreur de CI.
"""

import json
import os
import sys

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data", "catalogue-fr.json")
SEUIL_MIN = 5


def main():
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"::warning::Fichier introuvable: {OUTPUT_FILE} - le scraper n'a rien produit.")
        return 0
    except json.JSONDecodeError as e:
        print(f"::error::JSON invalide dans {OUTPUT_FILE}: {e}")
        return 1

    total = data.get("total", 0)
    sources = data.get("sources", [])
    maj = data.get("mise_a_jour", "n/a")

    print(f"Catalogue: {total} oeuvres")
    print(f"Sources  : {sources}")
    print(f"Mise a jour: {maj}")

    if total < SEUIL_MIN:
        print(
            f"::warning::Seulement {total} oeuvre(s) scrappee(s) "
            f"(seuil indicatif: {SEUIL_MIN}). Les sources sont probablement "
            "inaccessibles. Le workflow continue sans echouer."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
