"""The 35 OpenCritic endpoints. Every path is served with and without the
`/opencritic` prefix, so code generated against the hosted API on RapidAPI
(paths like /games/details) runs unchanged against this server.

Each route validates its query with the marshmallow schema in
opencritic/schemas.py (unknown params are rejected, ids and opencritic.com
links are both accepted), calls the endpoint function and maps failures to
HTTP: bad params -> 400, missing game / outlet / critic -> 404, OpenCritic
unreachable -> 502, anything else -> 500. Paginated endpoints answer with
count / per_page / current_page / total_pages / next / previous first."""
import json
from urllib.parse import urlencode

from bottle import request, response, route

from opencritic import (catalog, collections, community, critics, games, news, outlets, reviews,
                        schemas, search)
from schema_fields import load_query
from scraper_errors import BadRequest, Blocked, NotFound, UpstreamError


def json_response(data, status=200):
    response.status = status
    response.content_type = "application/json"
    return json.dumps(data, ensure_ascii=False)


def query_dict():
    """The request query as unicode strings (bottle 0.12's .get() hands back
    latin-1 decoded bytes, so a UTF-8 "Pokémon" would arrive as "PokÃ©mon")."""
    return {key: request.query.getunicode(key) for key in request.query.keys()}


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _page_link(path, params, page):
    if not page:
        return None
    query = {k: v for k, v in params.items() if v not in (None, "", False)}
    query["page"] = page
    scheme, host = request.urlparts.scheme, request.urlparts.netloc
    return f"{scheme}://{host}{path}?{urlencode(query, doseq=True)}"


def paginate(result, path, raw_params):
    """Lift the endpoint's `pagination` block into the flat shape with
    next / previous links built from the caller's own query params."""
    pagination = result.pop("pagination", None) or {}
    page = _as_int(pagination.get("page")) or _as_int(raw_params.get("page")) or 1
    total_pages = max(_as_int(pagination.get("total_pages")), 0)
    out = {
        "count": pagination.get("total_count"),
        "per_page": pagination.get("items_per_page"),
        "current_page": page,
        "total_pages": total_pages,
        "next": _page_link(path, raw_params, page + 1 if page < total_pages else None),
        "previous": _page_link(path, raw_params, page - 1 if page > 1 else None),
    }
    out.update(result)
    return out


def call(path, schema_cls, impl, paginated):
    raw = query_dict()
    data, error = load_query(schema_cls, raw)
    if error:
        return json_response(error, 400)
    try:
        result = impl(**data)
    except ValueError as e:
        return json_response({"error": str(e)}, 400)
    except BadRequest as e:
        return json_response({"error": f"opencritic rejected the request: {e}"}, 400)
    except NotFound as e:
        return json_response({"error": str(e) or "not found"}, 404)
    except Blocked as e:
        return json_response({"error": f"opencritic blocked the request, retry later: {e}"}, 502)
    except UpstreamError as e:
        return json_response({"error": f"opencritic {path.strip('/')} failed: {e}"}, 502)
    except Exception as e:
        return json_response({"error": f"opencritic {path.strip('/')} failed: {type(e).__name__}: {e}"}, 500)
    if paginated:
        result = paginate(result, request.path, raw)
    return json_response(result)


# (path, schema, endpoint function, paginated) — the order of the API docs
ENDPOINTS = [
    ("/games/details", schemas.GameSchema, games.details, False),
    ("/search", schemas.SearchSchema, search.search, False),
    ("/games/search", schemas.QuerySchema, games.search, False),
    ("/games", schemas.GameBrowseSchema, games.browse, True),
    ("/games/reviews", schemas.GameReviewsSchema, reviews.game_reviews, True),
    ("/games/reviews/all", schemas.GameSchema, reviews.game_reviews_all, False),
    ("/games/reviews/featured", schemas.GameSchema, reviews.game_reviews_featured, False),
    ("/games/score-distribution", schemas.GameSchema, reviews.score_distribution, False),
    ("/games/media", schemas.GameSchema, games.media, False),
    ("/games/user-rating", schemas.GameSchema, community.user_rating, False),
    ("/games/user-reviews", schemas.UserReviewsSchema, community.user_reviews, True),
    ("/games/news", schemas.GameSchema, news.game_news, False),
    ("/games/popular", schemas.EmptySchema, games.popular, False),
    ("/games/upcoming", schemas.EmptySchema, games.upcoming, False),
    ("/games/recently-released", schemas.EmptySchema, games.recently_released, False),
    ("/games/reviewed-today", schemas.EmptySchema, games.reviewed_today, False),
    ("/games/reviewed-this-week", schemas.EmptySchema, games.reviewed_this_week, False),
    ("/games/hall-of-fame", schemas.HallOfFameSchema, games.hall_of_fame, False),
    ("/games/deals", schemas.EmptySchema, games.deals, False),
    ("/calendar", schemas.EmptySchema, catalog.calendar, False),
    ("/outlets", schemas.OutletListSchema, outlets.list_outlets, True),
    ("/outlets/details", schemas.OutletSchema, outlets.details, False),
    ("/outlets/reviews", schemas.OutletReviewsSchema, reviews.outlet_reviews, True),
    ("/critics/search", schemas.QuerySchema, critics.search, False),
    ("/critics/details", schemas.CriticSchema, critics.details, False),
    ("/critics/reviews", schemas.CriticReviewsSchema, reviews.critic_reviews, True),
    ("/news", schemas.NewsSchema, news.list_news, True),
    ("/news/details", schemas.ArticleSchema, news.details, False),
    ("/collections", schemas.EmptySchema, collections.list_collections, False),
    ("/collections/details", schemas.CollectionSchema, collections.details, False),
    ("/collections/games", schemas.CollectionGamesSchema, collections.games, True),
    ("/platforms", schemas.EmptySchema, catalog.platforms, False),
    ("/genres", schemas.EmptySchema, catalog.genres, False),
    ("/tags", schemas.EmptySchema, catalog.tags, False),
    ("/score-formats", schemas.EmptySchema, catalog.score_formats, False),
]


def mount(path, schema_cls, impl, paginated):
    """Serve one endpoint at /path and /opencritic/path."""
    def handler():
        return call(path, schema_cls, impl, paginated)
    handler.__name__ = "opencritic_" + path.strip("/").replace("/", "_").replace("-", "_")
    route(path, method="GET")(handler)
    route("/opencritic" + path, method="GET")(handler)


for _path, _schema, _impl, _paginated in ENDPOINTS:
    mount(_path, _schema, _impl, _paginated)


@route("/", method="GET")
@route("/health", method="GET")
def health():
    return json_response({"status": "ok", "endpoints": [p for p, *_ in ENDPOINTS]})
