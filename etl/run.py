#!/usr/bin/env python3
"""Point d'entrée CLI de l'ETL Scanaddiction.

Exemples :
  python -m etl.run                       # tout, avec quality gate
  python -m etl.run --only mangadex       # une seule source
  python -m etl.run --no-min              # désactive le plancher (debug)
"""
import argparse
import logging
import sys

from . import pipeline


def main():
    ap = argparse.ArgumentParser(description="ETL catalogue Scanaddiction")
    ap.add_argument("--only", nargs="*", help="limiter à ces codes source")
    ap.add_argument("--no-min", action="store_true", help="désactiver le plancher qualité")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s : %(message)s",
        datefmt="%H:%M:%S",
    )

    meta, catalogue = pipeline.run(only=args.only, enforce_min=not args.no_min)

    print("=" * 60)
    print(f"Statut      : {meta['status']}")
    print(f"Séries      : {meta['total_series']}")
    print(f"Sources OK  : {meta['sources_ok']}")
    print(f"Sources KO  : {meta['sources_failed']}")
    print(f"Durée       : {meta['duration_sec']}s")
    if meta["notes"]:
        print(f"Notes       : {meta['notes']}")
    print("=" * 60)

    return 0 if meta["status"] in ("success", "partial") else 1


if __name__ == "__main__":
    sys.exit(main())
