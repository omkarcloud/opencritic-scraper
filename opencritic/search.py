"""OpenCritic combined search: games, outlets and critics in one call."""
from opencritic import fetch
from opencritic import parsers as P


def search(query, type=None):
    """Games, outlets and critics whose name is close to `query` (trigram
    similarity, `match` 1 = exact), 10 hits; `type` keeps one kind."""
    rows = fetch.api_get("meta/search", {"criteria": query})
    hits = [h for h in (P.search_hit(r) for r in rows or []) if h]
    if type:
        hits = [h for h in hits if h["type"] == type]
    return {"query": query, "results": hits}
