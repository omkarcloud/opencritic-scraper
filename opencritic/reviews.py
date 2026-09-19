"""OpenCritic critic reviews: paginated lists per game / outlet / critic,
the full review set of a game, the featured (landing) reviews and a score
distribution computed over the full set."""
from opencritic import fetch
from opencritic import parsers as P
from opencritic.shared import PAGE_SIZE, paged_result, skip_of

REVIEW_SORTS = ("newest", "oldest", "score-high", "score-low", "popularity", "blend")


def _paged(kind, entity_id, page, sort, order, total):
    params = {}
    if sort and sort != "blend":
        params["sort"] = sort
    if order:
        params["order"] = order
    if page > 1:
        params["skip"] = skip_of(page)
    rows = fetch.api_get(f"review/{kind}/{entity_id}", params, not_found=f"{kind} {entity_id}")
    return paged_result("results", P.reviews(rows), page, PAGE_SIZE, total,
                        sort=sort or "blend", order=order)


def _game_total(game_id):
    raw = fetch.api_get(f"game/{game_id}", not_found=f"game {game_id}")
    return P.to_int(raw.get("numReviews")), P.game_ref(raw)


def game_reviews(game, page=1, sort="blend", order=None):
    """Critic reviews of a game, 20 per page. sort: newest / oldest /
    score-high / score-low / popularity / blend (the site's default mix of
    recency and outlet popularity)."""
    total, game_ref = _game_total(game)
    out = _paged("game", game, page, sort, order, total)
    out["game"] = game_ref
    return out


def game_reviews_all(game):
    """Every critic review of a game in one call (no pagination)."""
    total, game_ref = _game_total(game)
    rows = fetch.api_get(f"review/game/{game}/all", not_found=f"game {game}")
    results = P.reviews(rows)
    return {"game": game_ref, "review_count": len(results), "expected_review_count": total, "results": results}


def game_reviews_featured(game):
    """The reviews OpenCritic features on the game's page (up to 8)."""
    _, game_ref = _game_total(game)
    rows = fetch.api_get(f"review/game/{game}/landing", not_found=f"game {game}")
    return {"game": game_ref, "results": P.reviews(rows)}


def score_distribution(game):
    """Histogram of a game's critic scores (what the site's charts tab
    draws): per-score counts, 5-point buckets, min / max / mean / median."""
    raw = fetch.api_get(f"game/{game}", not_found=f"game {game}")
    rows = fetch.api_get(f"review/game/{game}/all", not_found=f"game {game}")
    out = {"game": P.game_ref(raw), "top_critic_score": P.score(raw.get("topCriticScore")),
           "tier": P.clean(raw.get("tier")), "percentile": P.to_int(raw.get("percentile")),
           "percent_recommended": P.percent(raw.get("percentRecommended"))}
    out.update(P.score_distribution(rows))
    return out


def outlet_reviews(outlet, page=1, sort="newest", order=None):
    """Reviews published by an outlet, 20 per page, newest first by default."""
    raw = fetch.api_get(f"outlet/{outlet}", not_found=f"outlet {outlet}")
    out = _paged("outlet", outlet, page, sort, order, P.to_int(raw.get("numReviews")))
    out["outlet"] = P.outlet_ref(raw)
    return out


def critic_reviews(critic, page=1, sort="newest", order=None):
    """Reviews written by a critic, 20 per page, newest first by default."""
    raw = fetch.api_get(f"author/{critic}", not_found=f"critic {critic}")
    out = _paged("author", critic, page, sort, order, P.to_int(raw.get("numReviews")))
    out["critic"] = P.author_ref(raw)
    return out
