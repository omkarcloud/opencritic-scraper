"""OpenCritic collections (upstream "game sequences"): curated catalogues
such as Xbox Game Pass Ultimate with per-tier metrics and a sortable game
list."""
from opencritic import fetch
from opencritic import parsers as P
from opencritic.shared import PAGE_SIZE, paged_result, skip_of, tag_index

COLLECTION_SORTS = {"score": "score", "release-date": "date"}


def list_collections():
    """Every collection key and name."""
    rows = fetch.api_get("game-sequence/")
    return {"results": [c for c in (P.collection_summary(r) for r in rows or []) if c]}


def details(collection):
    """A collection: description, tier counts, every game id/name in it and
    the titles OpenCritic does not track."""
    raw = fetch.api_get(f"game-sequence/meta/{collection}", not_found=f"collection {collection}")
    if not isinstance(raw, dict) or not raw.get("key"):
        raise fetch.OpenCriticNotFound(f"collection {collection} not found")
    return P.collection(raw)


def games(collection, page=1, sort="score"):
    """The games of a collection as full records, 20 per page, by score or
    release date."""
    meta = fetch.api_get(f"game-sequence/meta/{collection}", not_found=f"collection {collection}")
    if not isinstance(meta, dict) or not meta.get("key"):
        raise fetch.OpenCriticNotFound(f"collection {collection} not found")
    params = {"sort": COLLECTION_SORTS[sort]}
    if page > 1:
        params["skip"] = skip_of(page)
    rows = fetch.api_get(f"game-sequence/games/{collection}", params)
    index = tag_index()
    total = P.to_int((meta.get("metrics") or {}).get("numGames"))
    if total is not None:
        total -= P.to_int((meta.get("metrics") or {}).get("notOnOpenCritic")) or 0
    results = [g for g in (P.game_details(r, index) for r in rows or []) if g]
    return paged_result("results", results, page, PAGE_SIZE, total,
                        collection={"key": P.clean(meta.get("key")), "name": P.clean(meta.get("label"))}, sort=sort)
