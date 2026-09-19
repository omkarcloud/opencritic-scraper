"""OpenCritic community data: the user rating summary of a game and the
paginated user reviews behind it."""
from opencritic import fetch
from opencritic import parsers as P
from opencritic.shared import paged_result

USER_REVIEW_SORTS = ("score", "newest")
USER_REVIEW_PAGE_SIZE = 20


def user_rating(game):
    """Median user score and how many users rated the game."""
    game_raw = fetch.api_get(f"game/{game}", not_found=f"game {game}")
    raw = fetch.api_get(f"ratings/game/{game}")
    count = fetch.api_get(f"ratings/game/{game}/reviews/count")
    out = {"game": P.game_ref(game_raw)}
    out.update(P.user_rating_summary(raw))
    out["review_count"] = P.to_int((count or {}).get("count")) if isinstance(count, dict) else None
    return out


def user_reviews(game, page=1, sort="score"):
    """Approved user reviews of a game, 20 per page, by score or newest."""
    game_raw = fetch.api_get(f"game/{game}", not_found=f"game {game}")
    count = fetch.api_get(f"ratings/game/{game}/reviews/count")
    total = P.to_int((count or {}).get("count")) if isinstance(count, dict) else None
    rows = fetch.api_get(f"ratings/game/{game}/reviews",
                         {"sort": sort, "limit": USER_REVIEW_PAGE_SIZE, "page": page})
    results = [r for r in (P.user_review(x) for x in rows or []) if r]
    return paged_result("results", results, page, USER_REVIEW_PAGE_SIZE, total,
                        game=P.game_ref(game_raw), sort=sort)
