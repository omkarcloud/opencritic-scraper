"""OpenCritic games: details, media, browse (filtered list), search and the
curated lists (popular, upcoming, recently released, reviewed today / this
week, hall of fame, deals)."""
from opencritic import fetch, refs
from opencritic import parsers as P
from opencritic.shared import PAGE_SIZE, paged_result, skip_of, tag_index

# public -> upstream tokens
GAME_SORTS = {"score": "score", "release-date": "firstReleaseDate", "name": "name",
         "review-count": "num-reviews", "percent-recommended": "percent-recommended"}
GAME_PERIODS = {"all-time": None, "last-90-days": "last90", "upcoming": "upcoming"}
# platform filter values = lower-cased shortName from /platform ("switch 2" keeps its space)
BROWSE_PLATFORMS = {"pc": "pc", "ps5": "ps5", "ps4": "ps4", "xbxs": "xbxs", "xb1": "xb1", "switch": "switch",
             "switch-2": "switch 2", "quest": "quest", "psvr": "psvr", "vive": "vive", "wii-u": "wii-u",
             "3ds": "3ds", "vita": "vita", "stadia": "stadia"}
HALL_OF_FAME_FIRST_YEAR = 2016


def _game(game_id, fullmedia=False):
    params = {"fullmedia": "true"} if fullmedia else None
    return fetch.api_get(f"game/{game_id}", params, not_found=f"game {game_id}")


def details(game):
    """Full game record: scores, tier, percentile, platforms with release
    dates, developers / publishers, genres, tags, stores with prices,
    images, trailers and the review-date milestones."""
    return P.game_details(_game(game), tag_index())


def media(game):
    """Every image set, screenshot and trailer of a game (the site's
    /media tab; upstream `fullmedia=true`)."""
    raw = _game(game, fullmedia=True)
    gid = P.to_int(raw.get("id"))
    return {
        "id": gid, "name": P.clean(raw.get("name")), "link": P.clean(raw.get("url")) or refs.game_link(gid, raw.get("name")),
        "images": P.images(raw.get("images"), gid),
        "legacy_images": P.game_details(raw)["legacy_images"],
        "trailers": [t for t in (P.trailer(x) for x in raw.get("trailers") or []) if t] or None,
        "youtube_channel": P.youtube_channel(raw.get("mainChannel")),
    }


def browse(page=1, platforms=None, period="all-time", year=None, tag=None, sort="score", order=None):
    """Filtered game list (the site's /browse pages): platforms, a release
    year OR a period (last-90-days / upcoming), a tag, sorted by score /
    release date / name / review count / percent recommended. 20 per page,
    no total count upstream."""
    params = {}
    if platforms:
        params["platforms"] = ",".join(BROWSE_PLATFORMS[p] for p in platforms)
    if year:
        params["time"] = str(year)
    elif GAME_PERIODS.get(period):
        params["time"] = GAME_PERIODS[period]
    if tag:
        params["tag"] = tag
    params["sort"] = GAME_SORTS[sort]
    if order:
        params["order"] = order
    if page > 1:
        params["skip"] = skip_of(page)
    rows = fetch.api_get("game", params)
    index = tag_index()
    results = [g for g in (P.game_card(r, index) for r in rows or []) if g]
    return paged_result("results", results, page, PAGE_SIZE,
                        filters={"platforms": platforms, "period": period if not year else None, "year": year,
                                 "tag": tag, "sort": sort, "order": order})


def search(query):
    """Games whose name is close to `query` (trigram similarity; `match` 1 =
    exact). 10 hits."""
    rows = fetch.api_get("game/search", {"criteria": query})
    return {"query": query, "results": [h for h in (P.search_hit(r, "game") for r in rows or []) if h]}


def _list(path, **params):
    rows = fetch.api_get(path, params or None)
    index = tag_index()
    return [g for g in (P.game_card(r, index) for r in rows or []) if g]


def popular():
    """The most popular games right now (page views + recent reviews +
    outlet notoriety), 48 rows."""
    return {"results": _list("game/popular")}


def upcoming():
    """The next 8 major releases."""
    return {"results": _list("game/upcoming")}


def recently_released():
    """The 8 most recently released major titles."""
    return {"results": _list("game/recently-released")}


def reviewed_today():
    """Games that received the most reviews today, with the count."""
    return {"results": _list("game/reviewed-today")}


def reviewed_this_week():
    """Games that received the most reviews this week, with the count."""
    return {"results": _list("game/reviewed-this-week")}


def hall_of_fame(year=None):
    """The 12 Hall of Fame games of `year` (2016 onwards; default = the
    current Hall of Fame year, which rolls over in early February)."""
    path = f"game/hall-of-fame/{year}" if year else "game/hall-of-fame"
    return {"year": year, "results": _list(path)}


def deals():
    """Games currently discounted at OpenCritic's partner stores, with the
    featured deal (store, price, base price, discount)."""
    rows = fetch.api_get("game/deals")
    index = tag_index()
    return {"results": [g for g in (P.deal_card(r, index) for r in rows or []) if g]}
