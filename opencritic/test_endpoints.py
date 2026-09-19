"""Offline tests for the OpenCritic refs, marshmallow schemas, parsers and
the endpoint functions with the transport monkeypatched to serve fixtures
(raw api.opencritic.com payloads captured 2026-09-19) — no network.

    python -m pytest opencritic/test_endpoints.py -q
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_fields import load_query  # noqa: E402
from opencritic import (catalog, collections, community, critics, fetch, games, news,  # noqa: E402
                        outlets, parsers as P, refs, reviews, schemas, search, shared)

FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def fixture(name):
    with open(os.path.join(FX, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


# api path -> fixture name (params ignored unless listed)
ROUTES = {
    "game/463": "game_463", "game": "game_list", "game/popular": "game_popular",
    "game/upcoming": "game_upcoming", "game/recently-released": "game_upcoming",
    "game/reviewed-today": "game_reviewed_today", "game/reviewed-this-week": "game_reviewed_this_week",
    "game/hall-of-fame/2024": "game_hof_2024", "game/hall-of-fame": "game_hof_2024",
    "game/deals": "game_deals", "game/tags": "game_tags", "game/search": "game_search",
    "meta/search": "meta_search", "author/search": "author_search",
    "review/game/463": "review_game_463", "review/game/463/landing": "review_game_463_landing",
    "review/game/463/all": "review_game_463_all", "review/outlet/56": "review_outlet_56",
    "review/author/481": "review_author_481", "outlet": "outlet_list", "outlet/56": "outlet_56",
    "author/481": "author_481", "article/list": "article_list", "article/36879": "article_36879",
    "article/game/463": "article_game_463", "calendar/v2": "calendar_v2",
    "game-sequence/": "sequences", "game-sequence/meta/xbox-game-pass-ultimate": "sequence_meta",
    "game-sequence/games/xbox-game-pass-ultimate": "sequence_games",
    "platform": "platform", "genre": "genre", "score-format": "score_format",
    "ratings/game/463": "ratings_game_463", "ratings/game/463/reviews": "ratings_game_463_reviews",
    "ratings/game/463/reviews/count": "ratings_game_463_count",
}


@pytest.fixture
def api(monkeypatch):
    calls = []

    def fake_get(path, params=None, not_found=None):
        calls.append((path, dict(params or {})))
        if path not in ROUTES:
            if not_found:
                raise fetch.OpenCriticNotFound(f"{not_found} not found")
            raise fetch.OpenCriticBadRequest("An unknown error has occurred")
        return fixture(ROUTES[path])

    monkeypatch.setattr(fetch, "api_get", fake_get)
    shared._tag_index["value"] = None
    return calls


def last(calls, path):
    """Params of the most recent call to `path` (the tag index may be fetched after it)."""
    return next(params for p, params in reversed(calls) if p == path)


# ---- refs / schemas ----------------------------------------------------------------------

@pytest.mark.parametrize("value", [
    "463", "https://opencritic.com/game/463/the-witcher-3-wild-hunt",
    "https://opencritic.com/game/463/the-witcher-3-wild-hunt/reviews?page=2",
    "opencritic.com/game/463/the-witcher-3-wild-hunt/charts", "https://www.opencritic.com/game/463",
])
def test_game_ref_forms(value):
    assert refs.resolve("game", value) == 463


def test_refs_reject_other_kinds_and_sites():
    with pytest.raises(ValueError):
        refs.resolve("game", "https://opencritic.com/outlet/56/ign")
    with pytest.raises(ValueError):
        refs.resolve("outlet", "https://www.metacritic.com/game/elden-ring")
    with pytest.raises(ValueError):
        refs.resolve("critic", "travis")
    assert refs.resolve("critic", "https://opencritic.com/critic/481/travis-northup") == 481
    assert refs.resolve("article", "https://opencritic.com/news/36879/x") == 36879
    assert refs.resolve_collection("Xbox-Game-Pass-Ultimate") == "xbox-game-pass-ultimate"


def test_slug_matches_site():
    assert refs.slugify("The Witcher 3: Wild Hunt") == "the-witcher-3-wild-hunt"
    assert refs.slugify("Baldur's Gate 3") == "baldurs-gate-3"
    assert refs.slugify("Pokémon Pokopia") == "pok-mon-pokopia"


def test_schemas():
    data, err = load_query(schemas.GameBrowseSchema, {
        "platforms": "PC, switch-2", "year": "2025", "tag": "Souls Like", "sort": "Release-Date"})
    assert err is None and data == {"page": 1, "platforms": ["pc", "switch-2"], "period": "all-time",
                                    "year": 2025, "tag": "souls-like", "sort": "release-date", "order": None}
    _, err = load_query(schemas.GameBrowseSchema, {"period": "week"})
    assert err and "period" in err["errors"]
    _, err = load_query(schemas.GameBrowseSchema, {"platforms": "gamecube"})
    assert err and "platforms" in err["errors"]
    _, err = load_query(schemas.HallOfFameSchema, {"year": "2015"})
    assert err and "year" in err["errors"]
    _, err = load_query(schemas.GameSchema, {"game": "463", "id": "463"})
    assert err and "id" in err["errors"]
    data, _ = load_query(schemas.GameReviewsSchema, {"game": "https://opencritic.com/game/463/x/reviews"})
    assert data == {"game": 463, "page": 1, "sort": "blend", "order": None}
    data, _ = load_query(schemas.OutletListSchema, {"contributors_only": "yes"})
    assert data["contributors_only"] is True and data["limit"] == 50


# ---- parsers ----------------------------------------------------------------------------

def test_value_helpers():
    assert P.iso_date("2015-05-19T00:00:00.000Z") == "2015-05-19"
    assert P.iso_datetime("2019-09-21T18:43:53.145Z") == "2019-09-21T18:43:53Z"
    assert P.score(-1) is None and P.score("92.536") == 92.54
    assert P.fraction_percent(0.85) == 85.0 and P.fraction_percent(0) is None
    assert P.image_link("game/463/o/x.jpg") == "https://img.opencritic.com/game/463/o/x.jpg"
    assert P.image_link("//c.opencritic.com/a.jpg") == "https://c.opencritic.com/a.jpg"
    assert P.image_set({"og": "game/undefined/o/a.jpg"}, 7) == {"original": "https://img.opencritic.com/game/7/o/a.jpg"}
    assert P.strip_html("<p>a &amp; b</p><p>c</p>") == "a & b\nc"


def test_no_verdict_review_is_unscored():
    raw = {"_id": "x", "score": 0, "npScore": None,
           "ScoreFormat": {"id": 30, "name": "No Verdict", "isNumeric": False, "isSelect": False}}
    out = P.review(raw)
    assert out["score"] is None and out["has_verdict"] is False and out["outlet_score"] is None


def test_review_outlet_scale_and_hidden_link():
    fmt = {"id": 19, "isNumeric": True, "base": 20, "numDecimals": 2}
    out = P.review({"_id": "y", "score": 90, "npScore": 100, "ScoreFormat": fmt,
                    "externalUrl": "https://x", "hideReviewUrl": True, "alias": "Someone"})
    assert out["score"] == 90.0 and out["outlet_score"] == 4.5 and out["link"] is None
    assert out["authors"] == [{"id": None, "name": "Someone", "link": None, "image": None}]


def test_parsers_never_crash_on_partial_input():
    for fn in (P.game_card, P.game_details, P.review, P.outlet, P.critic, P.article, P.collection,
               P.user_review, P.calendar_game, P.store, P.trailer):
        assert fn({}) is not None
        assert fn(None) is None
    assert P.score_distribution([])["scored_review_count"] == 0


# ---- endpoints -------------------------------------------------------------------------

def test_game_details(api):
    out = games.details(463)
    assert out["id"] == 463 and out["link"] == "https://opencritic.com/game/463/the-witcher-3-wild-hunt"
    assert out["tier"] == "Mighty" and out["top_critic_score"] == 92.54 and out["esrb_rating"] == "M"
    assert out["developers"] == ["CD Projekt Red"]
    assert {"id": "adventure", "name": "Adventure"} in out["tags"]      # mongo id -> slug via /game/tags
    gog = next(s for s in out["stores"] if s["store"] == "GOG")
    assert gog["price"] == 49.99 and gog["currency"] == "USD"
    assert out["images"]["box"]["original"].startswith("https://img.opencritic.com/game/463/")
    assert out["dates"]["first_review"] == "2015-05-11"
    assert not any(k.startswith("_") for k in out)


def test_game_not_found(api):
    with pytest.raises(fetch.OpenCriticNotFound):
        games.details(999999999)


def test_browse_maps_filters(api):
    out = games.browse(page=3, platforms=["pc", "switch-2"], year=2025, tag="action", sort="release-date", order="asc")
    assert last(api, "game") == {"platforms": "pc,switch 2", "time": "2025", "tag": "action",
                                          "sort": "firstReleaseDate", "order": "asc", "skip": 40}
    assert len(out["results"]) == 20 and out["pagination"]["total_pages"] == 4
    assert out["results"][0]["release_date"] and out["results"][0]["platforms"]
    games.browse(period="last-90-days")
    assert last(api, "game") == {"time": "last90", "sort": "score"}


def test_curated_lists(api):
    assert len(games.popular()["results"]) == 48
    today = games.reviewed_today()["results"][0]
    assert today["recent_review_count"] == 2
    deal = games.deals()["results"][0]
    assert deal["biggest_discount_percent"] == 85.0
    assert deal["featured_deal"] == {"store": "GOG", "link": "https://af.gog.com/game/control_ultimate_edition?as=1673677962",
                                     "price": 5.99, "base_price": 39.99, "currency": "USD", "discount_percent": 85}
    assert games.hall_of_fame(2024)["year"] == 2024


def test_search(api):
    hit = search.search("ign")["results"][0]
    assert hit == {"type": "outlet", "id": 56, "name": "IGN", "link": "https://opencritic.com/outlet/56/ign", "match": 1.0}
    assert {h["type"] for h in search.search("ign", type="game")["results"]} == {"game"}
    assert search.search("ign", type="critic")["results"] == []
    assert P.search_hit({"id": 1, "name": "A B", "dist": 0.5, "relation": "critic"})["type"] == "critic"
    assert games.search("witcher")["results"][0]["type"] == "game"
    assert critics.search("travis")["results"][0]["type"] == "critic"


def test_game_reviews_paging(api):
    out = reviews.game_reviews(463, page=2, sort="score-high")
    assert last(api, "review/game/463") == {"sort": "score-high", "skip": 20}
    assert out["pagination"] == {"page": 2, "items_per_page": 20, "total_pages": 10, "total_count": 181}
    r = out["results"][0]
    assert r["outlet"]["name"] and r["game"]["id"] == 463 and r["published_at"]
    reviews.game_reviews(463)
    assert last(api, "review/game/463") == {}      # blend = upstream default, no sort param


def test_score_distribution(api):
    out = reviews.score_distribution(463)
    assert out["review_count"] == 181
    assert out["scored_review_count"] + out["unscored_review_count"] == 181
    assert out["min_score"] > 0                        # the No Verdict 0 is excluded
    assert sum(b["count"] for b in out["buckets"]) == out["scored_review_count"]


def test_outlet_and_critic(api):
    o = outlets.details(56)
    assert o["name"] == "IGN" and o["recommended_cutoff"] == 70.0 and o["score_format"]["base"] == 10
    c = critics.details(481)
    assert c["socials"]["linkedin"] == "https://www.linkedin.com/in/travis-northup-14586115"
    assert c["email"] and c["review_count"] == 219
    rv = reviews.outlet_reviews(56, page=2)
    assert rv["outlet"]["id"] == 56 and last(api, "review/outlet/56") == {"sort": "newest", "skip": 20}
    listing = outlets.list_outlets(limit=5, sort="name")
    assert listing["pagination"]["total_count"] == 30 and len(listing["results"]) == 5


def test_news(api):
    item = news.list_news()["results"][0]
    assert item["type"] == "syndicated" and item["authors"] == ["Mohsen Baqery"]
    assert item["description"] is None                 # identical to teaser
    art = news.details(36879)
    assert art["body_text"] and art["link"].startswith("https://opencritic.com/news/36879/")
    assert news.game_news(463)["results"][0]["related_games"][0]["id"] == 463


def test_collections(api):
    assert collections.list_collections()["results"][0]["key"] == "xbox-game-pass-ultimate"
    d = collections.details("xbox-game-pass-ultimate")
    assert d["game_count"] == 538 and d["tier_counts"]["mighty"] == 96
    g = collections.games("xbox-game-pass-ultimate", page=2, sort="release-date")
    assert last(api, "game-sequence/games/xbox-game-pass-ultimate") == {"sort": "date", "skip": 20}
    assert g["pagination"]["total_count"] == 538 - 109
    assert g["results"][0]["review_summary"]["points"][0]["sentiment"] == "pro"


def test_community(api):
    r = community.user_rating(463)
    assert r["median_score"] == 100.0 and r["rating_count"] == 901 and r["review_count"] == 77
    u = community.user_reviews(463, sort="newest")
    row = u["results"][0]
    assert row["user"]["link"] == "https://opencritic.com/rmomb/ratings" and row["is_recommended"] is True


def test_catalog(api):
    plats = catalog.platforms()["results"]
    assert {"switch-2", "pc"} <= {p["filter_value"] for p in plats}
    assert catalog.tags()["results"][0]["id"]
    cal = catalog.calendar()
    assert cal["start_date"] == "2026-01-01" and cal["game_count"] == len(cal["games"])
    assert "undefined" not in json.dumps(cal)
