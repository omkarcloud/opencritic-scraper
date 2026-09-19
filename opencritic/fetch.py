"""OpenCritic transport: plain curl_cffi with browser-impersonated TLS
against api.opencritic.com — the same JSON API opencritic.com's Angular app
calls in the browser and the one RapidAPI proxies for the official listing.
No browser, no cookies, no login (validated 2026-09-19 from direct Indian
egress and a US residential proxy exit; 120 requests over 12 workers in 7 s with
no 429 and no rate-limit headers).

Authorisation: the site's main bundle (opencritic.com/main.<hash>.js) ships
a static API key in its environment module and its HTTP interceptor sends
it as `Authorization: Bearer <base64(key)>` on every request. This module
harvests that key from the bundle at first use, caches it and re-harvests
once when the API answers 400 "API key is required" (the key only changes
when OpenCritic rebuilds the bundle). config.OPENCRITIC_API_KEY pins one by
hand.

Surfaces (all GET, all under /api/):
  game/{id}[?fullmedia=true]         game record (+ every screenshot/trailer)
  game?platforms&time&sort&order&tag&skip      browse (20 per page)
  game/search|popular|upcoming|recently-released|reviewed-today|
       reviewed-this-week|hall-of-fame[/{year}]|deals|tags
  review/{game|outlet|author}/{id}?sort&order&skip   20 per page
  review/game/{id}/landing | /all    featured 8 | every review
  outlet | outlet/{id} | author/{id} | author/search | meta/search
  article/list?skip | article/{id} | article/game/{id}
  calendar/v2 | game-sequence/ | game-sequence/meta/{key} |
  game-sequence/games/{key}?sort&skip
  ratings/game/{id} | ratings/game/{id}/reviews?sort&limit&page | …/count
  platform | genre | score-format

Upstream quirks handled here: a missing entity and a bad enum value both
come back as HTTP 400 {"message": "An unknown error has occurred"} (callers
pass `not_found=` so a detail lookup turns into a 404); an unknown API path
is an HTML 404 "Cannot GET"; `limit` is ignored everywhere (fixed 20 rows,
`skip` pages); the game list rejects time=week/month/year/today/all-time.

FALLBACK HOOK: if api.opencritic.com ever starts refusing server IPs
(403/429 on every call) route it through a proxy (config.opencritic_proxy()
returns the URL the session uses); if the key harvest itself gets challenged, escalate the
way g2 does — a patchright pool with flag "opencritic" in config.CHROME_POOLS
that opens https://opencritic.com/ and runs the same GETs through the
in-page fetch (patchright_driver.FetchResponse). Not built: dead code while
plain HTTP works.

Failure taxonomy (scraper_errors, mapped to HTTP by route_glue):
  OpenCriticUpstreamError  transport failure / 5xx / non-JSON body  — retryable
  OpenCriticBlocked        403 / 429 / key refused after re-harvest  — retryable
  OpenCriticBadRequest     upstream rejected the params              — never retried
  OpenCriticNotFound       entity does not exist                     — never retried
"""
import base64
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from scraper_errors import BadRequest, Blocked, NotFound, UpstreamError

SITE = "https://opencritic.com"
API = "https://api.opencritic.com/api/"
IMPERSONATE = "chrome"
TIMEOUT = 30
RETRIES = 2                 # transport failures / 5xx per call
FANOUT_WORKERS = 6
KEY_RECHECK_INTERVAL = 300  # seconds between forced re-harvests after a refusal

PAGE_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
}
_BUNDLE_RE = re.compile(r'src="(main\.[0-9a-f]{8,}\.js)"')
_KEY_RE = re.compile(r'apiKey:"([A-Za-z0-9_\-]{16,})"')
_KEY_REQUIRED = "api key is required"
_UNKNOWN_ERROR = "unknown error"


class OpenCriticUpstreamError(UpstreamError):
    """Transport failure, 5xx or a non-JSON body — retryable."""


class OpenCriticBlocked(OpenCriticUpstreamError, Blocked):
    """403 / 429, or the harvested key keeps being refused — retryable."""


class OpenCriticBadRequest(BadRequest):
    """Upstream rejected the request (bad filter / sort value) — never retried."""


class OpenCriticNotFound(NotFound):
    """Entity does not exist — never retried."""


class _KeyRejected(OpenCriticUpstreamError):
    """400 "API key is required": the bundled key rotated — re-harvest once."""


class _EmptyBody(OpenCriticUpstreamError):
    """200 with an empty body: how upstream answers an unknown outlet id or
    collection key (a NotFound when the caller named the entity)."""


# ---- sessions (one per worker thread) --------------------------------------------

_local = threading.local()


def _session():
    sess = getattr(_local, "session", None)
    if sess is None:
        from curl_cffi import requests as curl_requests
        sess = curl_requests.Session(impersonate=IMPERSONATE)
        proxy = config.opencritic_proxy()
        if proxy:
            sess.proxies = {"http": proxy, "https": proxy}
        _local.session = sess
    return sess


def _drop_session():
    sess = getattr(_local, "session", None)
    _local.session = None
    if sess is not None:
        try:
            sess.close()
        except Exception:
            pass


def dump_debug(name, text):
    """Write a raw response to $OPENCRITIC_DEBUG_DIR/<name>.txt."""
    dbg = os.environ.get("OPENCRITIC_DEBUG_DIR", "")
    if dbg and text:
        try:
            os.makedirs(dbg, exist_ok=True)
            with open(os.path.join(dbg, name + ".txt"), "w") as f:
                f.write(text)
        except OSError:
            pass


# ---- API key (harvested from the site's main bundle) ---------------------------------

_key_lock = threading.Lock()
_key = {"value": None, "checked_at": 0.0}


def key_from_bundle(js_text):
    """The `apiKey:"…"` literal of the environment module, None if absent."""
    match = _KEY_RE.search(js_text or "")
    return match.group(1) if match else None


def bundle_name(html):
    match = _BUNDLE_RE.search(html or "")
    return match.group(1) if match else None


def _harvest_key():
    sess = _session()
    try:
        shell = sess.get(SITE + "/", headers=PAGE_HEADERS, timeout=TIMEOUT)
    except Exception as e:
        raise OpenCriticUpstreamError(f"opencritic.com request failed: {type(e).__name__}: {e}")
    if shell.status_code in (403, 429):
        dump_debug("shell_blocked", shell.text)
        raise OpenCriticBlocked(f"HTTP {shell.status_code} on opencritic.com")
    name = bundle_name(shell.text)
    if not name:
        dump_debug("shell", shell.text)
        raise OpenCriticUpstreamError(f"main bundle not referenced by opencritic.com (HTTP {shell.status_code}; layout changed?)")
    try:
        bundle = sess.get(f"{SITE}/{name}", headers=PAGE_HEADERS, timeout=TIMEOUT)
    except Exception as e:
        raise OpenCriticUpstreamError(f"bundle request failed: {type(e).__name__}: {e}")
    key = key_from_bundle(bundle.text)
    if not key:
        raise OpenCriticUpstreamError(f"no apiKey literal in {name} (HTTP {bundle.status_code}; bundle changed?)")
    return key


def api_key(force=False):
    """The bundled key: config.OPENCRITIC_API_KEY when pinned, else harvested
    once per process and re-harvested (at most every KEY_RECHECK_INTERVAL
    seconds) when `force` says the API refused it."""
    if config.OPENCRITIC_API_KEY:
        return config.OPENCRITIC_API_KEY
    with _key_lock:
        now = time.time()
        stale = force and now - _key["checked_at"] >= KEY_RECHECK_INTERVAL
        if _key["value"] is None or stale:
            _key["value"] = _harvest_key()
            _key["checked_at"] = now
        return _key["value"]


def _auth_headers(force=False):
    token = base64.b64encode(api_key(force=force).encode("utf-8")).decode("ascii")
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": f"Bearer {token}",
        "origin": SITE,
        "referer": SITE + "/",
    }


# ---- JSON GET ----------------------------------------------------------------------

def _message(body):
    if isinstance(body, dict):
        return str(body.get("message") or body.get("error") or "")
    return ""


def _get_once(path, params, force_key):
    sess = _session()
    try:
        resp = sess.get(API + path, params=params or None, headers=_auth_headers(force_key), timeout=TIMEOUT)
    except Exception as e:
        _drop_session()
        raise OpenCriticUpstreamError(f"{path}: {type(e).__name__}: {e}")
    status = resp.status_code
    text = resp.text or ""
    try:
        body = resp.json()
    except ValueError:
        body = None
    if status == 200:
        if body is not None:
            return body
        if not text.strip():
            # an unknown outlet id / collection key answers 200 with an empty body
            raise _EmptyBody(f"empty body on {path}")
    if status in (403, 429):
        dump_debug("blocked", text)
        raise OpenCriticBlocked(f"HTTP {status} on {path}")
    if status == 400:
        msg = _message(body)
        if _KEY_REQUIRED in msg.lower():
            raise _KeyRejected(msg)
        raise OpenCriticBadRequest(msg or f"HTTP 400 on {path}")
    if status == 404:
        raise OpenCriticNotFound(f"{path} does not exist on api.opencritic.com")
    if status >= 500:
        raise OpenCriticUpstreamError(f"HTTP {status} on {path}")
    dump_debug("unexpected", text)
    raise OpenCriticUpstreamError(f"HTTP {status} with a non-JSON body on {path}")


def api_get(path, params=None, not_found=None):
    """GET api.opencritic.com/api/<path> -> parsed JSON. `not_found` names the
    entity so upstream's 400 "unknown error" for a missing id becomes an
    OpenCriticNotFound; without it that 400 is an OpenCriticBadRequest."""
    force_key = False
    key_retried = False
    attempt = 0
    while True:
        try:
            return _get_once(path, params, force_key)
        except _KeyRejected as e:
            if key_retried:
                raise OpenCriticBlocked(f"api.opencritic.com refuses the bundled key: {e}")
            key_retried, force_key = True, True
        except OpenCriticBadRequest as e:
            if not_found and _UNKNOWN_ERROR in str(e).lower():
                raise OpenCriticNotFound(f"{not_found} not found")
            raise
        except _EmptyBody as e:
            if not_found:
                raise OpenCriticNotFound(f"{not_found} not found")
            raise OpenCriticUpstreamError(str(e))
        except OpenCriticNotFound:
            if not_found:
                raise OpenCriticNotFound(f"{not_found} not found")
            raise
        except OpenCriticBlocked:
            raise
        except OpenCriticUpstreamError:
            attempt += 1
            if attempt > RETRIES:
                raise
            time.sleep(0.5 * attempt)


def fanout(fn, items, workers=FANOUT_WORKERS):
    """fn(item) for every item, in parallel, results in order."""
    items = list(items)
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        return list(pool.map(fn, items))
