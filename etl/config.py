"""Configuration centrale de l'ETL."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
BUILD_DIR = os.path.join(ROOT, "build")
CATALOGUE_JSON = os.path.join(DATA_DIR, "catalogue-fr.json")
UPSERT_SQL = os.path.join(BUILD_DIR, "upsert.sql")

# Réseau
USER_AGENT = "Scanaddiction/2.0 (catalogue-fr; +https://github.com/Lydia-meftah/scanaddiction)"
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)
DELAY = float(os.environ.get("SCAN_DELAY", "1.2"))   # politesse entre requêtes
RETRY_TOTAL = 3
RETRY_BACKOFF = 0.6                                   # 0.6s, 1.2s, 2.4s
RETRY_STATUS = (429, 500, 502, 503, 504)

# Qualité (quality gate)
MIN_SERIES = int(os.environ.get("SCAN_MIN_SERIES", "50"))
VALID_TYPES = {"manga", "manhwa", "manhua"}
VALID_STATUTS = {"en cours", "terminé", "pause", "annulé"}
REQUIRED_FIELDS = ("id", "titre", "url", "source_code")

# Plafonds par source (bornent le temps de run)
MDX_MAX_OFFSET = 500
SM_MAX_SERIES = 200
CRUNCHYSCAN_MAPS = 4
SUSHISCAN_MAPS = 3
RAIJIN_MAPS = 30
