"""OpenCritic reference data and the release calendar: platforms, genres,
tags, score formats, the calendar window."""
from opencritic import fetch
from opencritic import parsers as P


def platforms():
    """Every platform with its id, name, short name and icon. The short
    name (lower-cased, 'switch 2' as 'switch-2') is the browse filter value."""
    rows = fetch.api_get("platform")
    results = sorted((p for p in (P.platform(r) for r in rows or []) if p),
                     key=lambda p: -(P.to_int(next((r.get("order") for r in rows if r.get("id") == p["id"]), 0)) or 0))
    for p in results:
        p["filter_value"] = (p["short_name"] or "").lower().replace(" ", "-") or None
    return {"results": results}


def genres():
    """Every genre with its id and name."""
    rows = fetch.api_get("genre")
    return {"results": sorted((g for g in (P.genre(r) for r in rows or []) if g), key=lambda g: g["name"] or "")}


def tags():
    """Every tag with its filter slug (the browse `tag` value)."""
    rows = fetch.api_get("game/tags")
    return {"results": sorted((t for t in (P.tag(r) for r in rows or []) if t), key=lambda t: t["name"] or "")}


def score_formats():
    """Every review score format outlets use: scale, base, decimals, stars or select."""
    rows = fetch.api_get("score-format")
    return {"results": [f for f in (P.score_format(r) for r in rows or []) if f]}


def calendar():
    """The release calendar window the site shows: title, date range,
    the games releasing in it and any events."""
    raw = fetch.api_get("calendar/v2")
    games = [g for g in (P.calendar_game(x) for x in raw.get("games") or []) if g]
    games.sort(key=lambda g: g["release_date"] or "")
    return {
        "title": P.clean(raw.get("title")),
        "start_date": P.iso_date(raw.get("startDate")),
        "end_date": P.iso_date(raw.get("endDate")),
        "game_count": len(games),
        "events": [e for e in (P.calendar_event(x) for x in raw.get("entries") or []) if e] or None,
        "games": games,
    }
