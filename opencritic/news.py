"""OpenCritic news: the syndicated article feed, one article with its body,
and the articles about a game."""
from opencritic import fetch
from opencritic import parsers as P
from opencritic.shared import ARTICLE_PAGE_SIZE, paged_result, skip_of


def list_news(page=1):
    """The news feed, newest first, 10 per page (no total upstream)."""
    params = {"skip": skip_of(page, ARTICLE_PAGE_SIZE)} if page > 1 else None
    rows = fetch.api_get("article/list", params)
    results = [a for a in (P.article(r) for r in rows or []) if a]
    return paged_result("results", results, page, ARTICLE_PAGE_SIZE)


def details(article):
    """One article with its HTML body and a plain-text rendering."""
    raw = fetch.api_get(f"article/{article}", not_found=f"article {article}")
    if not isinstance(raw, dict) or not raw.get("id"):
        raise fetch.OpenCriticNotFound(f"article {article} not found")
    return P.article(raw, with_body=True)


def game_news(game):
    """Articles OpenCritic has linked to a game (with bodies)."""
    game_raw = fetch.api_get(f"game/{game}", not_found=f"game {game}")
    rows = fetch.api_get(f"article/game/{game}")
    results = [a for a in (P.article(r, with_body=True) for r in rows or []) if a]
    return {"game": P.game_ref(game_raw), "count": len(results), "results": results}
