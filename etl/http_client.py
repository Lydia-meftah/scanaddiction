"""
Client HTTP durci et réutilisable.
Pattern recommandé (urllib3 Retry + HTTPAdapter monté sur une Session),
avec backoff exponentiel, respect de Retry-After et timeouts par requête.
Réf : peterbe.com/plog/best-practice-with-retries-with-requests
"""
import logging
import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except ImportError:  # très vieux urllib3
    from requests.packages.urllib3.util.retry import Retry

from . import config

log = logging.getLogger("etl.http")


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=config.RETRY_TOTAL,
        connect=config.RETRY_TOTAL,
        read=config.RETRY_TOTAL,
        status=config.RETRY_TOTAL,
        backoff_factor=config.RETRY_BACKOFF,
        status_forcelist=config.RETRY_STATUS,
        allowed_methods=frozenset(["GET", "HEAD"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    })
    return session


def get(session: requests.Session, url: str, **kwargs):
    """GET avec timeout par défaut. Renvoie la réponse ou None (log l'échec)."""
    kwargs.setdefault("timeout", config.TIMEOUT)
    try:
        r = session.get(url, **kwargs)
        if r.status_code != 200:
            log.warning("HTTP %s — %s", r.status_code, url)
            return None
        return r
    except requests.RequestException as e:
        log.warning("échec %s : %s", url, e)
        return None
