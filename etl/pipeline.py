"""Orchestration : extract (tolérant aux pannes) → transform → validate → load."""
import logging
import time
from datetime import datetime, timezone

from . import config, load, sources
from .http_client import build_session
from .models import normalize, validate

log = logging.getLogger("etl.pipeline")


def run(only=None, enforce_min=True):
    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    session = build_session()

    raw, ok, failed = [], [], []
    for code, fn in sources.REGISTRY:
        if only and code not in only:
            continue
        try:
            items = fn(session)
            log.info("source %-12s → %d", code, len(items))
            if items:
                load.save_raw(code, "\n".join(r["url"] for r in items))
            raw.extend(items)
            ok.append(code)
        except Exception as e:                       # une source ne tue pas le run
            log.error("source %s en échec : %s", code, e)
            failed.append(code)

    records = [normalize(r) for r in raw]
    valid, errors = validate(records)
    for e in errors[:20]:
        log.warning("validation: %s", e)

    status = "failed" if not valid else ("partial" if failed else "success")
    meta = {
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "status": status, "total_series": len(valid),
        "sources_ok": ok, "sources_failed": failed,
        "duration_sec": round(time.monotonic() - t0, 1),
        "notes": f"{len(errors)} erreurs de validation" if errors else "",
    }

    # Quality gate + filet de sécurité : ne jamais écraser un bon catalogue par du vide.
    if enforce_min and len(valid) < config.MIN_SERIES:
        meta["status"] = "failed"
        meta["notes"] = f"{len(valid)} séries < plancher {config.MIN_SERIES} — sorties NON écrites"
        log.error(meta["notes"])
        return meta, None

    catalogue = load.write_json(valid)
    load.write_upsert_sql(valid, meta)
    log.info("écrit : %d séries, sources=%s", catalogue["total"], catalogue["sources"])
    return meta, catalogue
