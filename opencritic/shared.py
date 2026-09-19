"""Helpers shared by the OpenCritic endpoint modules: fixed-size paging
(upstream serves 20 rows per `skip` window), the tag index that resolves
the Mongo tag ids list rows carry, and the paged result envelope."""
import threading
import time

from opencritic import fetch
from opencritic import parsers as P

PAGE_SIZE = 20             # every review / game list window upstream
ARTICLE_PAGE_SIZE = 10
TAG_INDEX_TTL = 6 * 3600

_tag_lock = threading.Lock()
_tag_index = {"value": None, "at": 0.0}


def skip_of(page, size=PAGE_SIZE):
    return (page - 1) * size


def tag_index():
    """{mongo id: {id (slug), name}} from /game/tags, refreshed every 6 h;
    an empty dict when the list cannot be fetched (tags are then dropped,
    never a failure of the calling endpoint)."""
    with _tag_lock:
        if _tag_index["value"] is not None and time.time() - _tag_index["at"] < TAG_INDEX_TTL:
            return _tag_index["value"]
        try:
            rows = fetch.api_get("game/tags")
        except Exception:
            return _tag_index["value"] or {}
        index = {}
        for t in rows or []:
            if isinstance(t, dict) and t.get("_id"):
                index[t["_id"]] = P.tag(t)
        _tag_index["value"], _tag_index["at"] = index, time.time()
        return index


def paged_result(key, results, page, per_page, total=None, has_more=None, **extra):
    """Endpoint result with a `pagination` block route_glue lifts."""
    if has_more is None:
        if total is None:
            has_more = len(results) >= per_page      # full window -> maybe more
        else:
            has_more = skip_of(page, per_page) + len(results) < total
    out = dict(extra)
    out[key] = results
    out["pagination"] = P.pagination(page, per_page, total, has_more)
    return out
