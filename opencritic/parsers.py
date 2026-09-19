"""OpenCritic payload normalizers: api.opencritic.com JSON -> one clean
snake_case shape per entity type.

Conventions: `link` for web URLs (opencritic.com pages, review/article
sources), image variants as absolute img.opencritic.com links keyed by size
(original / thumbnail / xs / small / medium / large / xl / xxl), dates as
YYYY-MM-DD for release / review / calendar days and full UTC ISO datetimes
for timestamps, scores as numbers rounded to 2 decimals, percentages as
0-100 numbers, `is_*` / `has_*` booleans, null for anything missing.

Upstream fields dropped on purpose (and why):
  * _id / __v / *._id on sub-documents (Mongo internals; `id` is the public
    id — review ids ARE the Mongo id since reviews have no other one),
    createdAt / updatedAt on list rows (kept as created_at / updated_at on
    detail records only), imageMigrationComplete, needsAdminDealReview,
    nextPriceScanTime, adminPriority, adminReviewed, externalSourcesConnected,
    newsSearchEnabled, isEligibleForDealFocus, oldObject (admin / pipeline
    state).
  * the stored 0 on "No Verdict" reviews (score format 30) — nulled, with
    has_verdict=false, so it never drags an average or a histogram down.
  * magic / magicSortField (the outlet popularity weight behind the
    "popularity" sort — an internal ranking number), isQuoteManual (how the
    snippet was entered), hideReviewUrl (applied: the link is nulled),
    hidePublicationUrls (applied the same way on outlets), lastRefreshDate.
  * Rating.imageSrc (an ESRB symbol image — kept as `esrb_rating` letter
    parsed from the file name), monetizationFeatures.summary (empty
    everywhere; hasLootBoxes is kept), mainChannel.image (YouTube avatar),
    Skus / type / twitchName / steamId on collection rows (partial, mostly
    null — steam_id is kept when present), discount / Affiliate.discount
    (duplicates of biggest_discount_*), isFeatured / isHomepage flags of the
    site's homepage layout, displayRelease (always null), imageSrc on
    Platforms (a static per-platform icon; platform ids are enough),
    initialPopularity on tags (a seed weight), score-format `options`
    (null on every format in use), calendar tagLine (= title).
  * article `description` when identical to `teaser` (same text),
    ratings `game` sub-document (the caller already knows the game),
    `count` / `declineReason` / `recommendTo` on user reviews (always 0 /
    null / [] for approved reviews; recommend_to kept when non-empty).
"""
import html as _html
import re
from datetime import datetime, timezone

from opencritic import refs

IMG = "https://img.opencritic.com/"
_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<br\s*/?>|</p>\s*<p>|</li>\s*<li>|</h\d>", re.I)
_ESRB_RE = re.compile(r"ratingsymbol_([a-z0-9]+)\.", re.I)
_SIZE_NAMES = {"og": "original", "th": "thumbnail", "xs": "xs", "sm": "small", "md": "medium",
               "lg": "large", "xl": "xl", "xxl": "xxl"}
_COMPANY_TYPES = {"DEVELOPER": "developers", "PUBLISHER": "publishers"}
_ESRB = {"e": "E", "e10": "E10+", "t": "T", "m": "M", "ao": "AO", "rp": "RP", "ec": "EC"}

TIERS = ("Mighty", "Strong", "Fair", "Weak")


# ---- value helpers ----------------------------------------------------------

def clean(value):
    """'' / [] / {} -> None (uniform nulls); strings are stripped."""
    if isinstance(value, str):
        value = value.strip()
    return None if value in ("", [], {}, None) else value


def to_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def to_float(value, digits=2):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, digits) if digits is not None else number


def score(value):
    """Scores are -1 / null before a game has enough reviews."""
    number = to_float(value)
    return None if number is None or number < 0 else number


def percent(value):
    """0-100 percentage (percentRecommended); -1 / null -> None."""
    return score(value)


def fraction_percent(value):
    """0.85 -> 85.0 (biggestDiscountPercentage is a fraction)."""
    number = to_float(value, 4)
    if number is None or number <= 0:
        return None
    return round(number * 100, 2)


def iso_date(value):
    """'2015-05-19T00:00:00.000Z' -> '2015-05-19' (UTC calendar day)."""
    dt = _parse(value)
    return dt.date().isoformat() if dt else None


def iso_datetime(value):
    """Full UTC ISO 8601 timestamp, seconds precision."""
    dt = _parse(value)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z") if dt else None


def _parse(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def strip_html(value):
    """HTML fragment -> plain text (paragraph / list breaks -> newlines)."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = _BR_RE.sub("\n", value)
    text = _html.unescape(_TAG_RE.sub("", text))
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return clean("\n".join(line for line in lines if line))


def image_link(path):
    """Image path or protocol-relative link -> absolute https link."""
    path = clean(path)
    if not path or not isinstance(path, str):
        return None
    if path.startswith("//"):
        return "https:" + path
    if path.startswith(("http://", "https://")):
        return path
    return IMG + path.lstrip("/")


def image_set(obj, game_id=None):
    """{og, sm, …} -> {original, small, …} as absolute links. `game_id`
    repairs the 'game/undefined/…' paths the calendar hands back."""
    if not isinstance(obj, dict):
        return None
    out = {}
    for size, name in _SIZE_NAMES.items():
        link = image_link(obj.get(size))
        if link and game_id is not None and "/undefined/" in link:
            link = link.replace("/undefined/", f"/{game_id}/")
        if link:
            out[name] = link
    return out or None


def images(obj, game_id=None):
    """A game's `images` block: box / square / masthead / banner / logo sets
    plus screenshots (list of sets)."""
    if not isinstance(obj, dict):
        return None
    out = {}
    for key in ("box", "square", "masthead", "banner", "logo"):
        out[key] = image_set(obj.get(key), game_id)
    shots = [image_set(s, game_id) for s in obj.get("screenshots") or [] if isinstance(s, dict)]
    out["screenshots"] = [s for s in shots if s] or None
    return out if any(out.values()) else None


def legacy_image(obj):
    """{fullRes, thumbnail} (c.opencritic.com) -> {original, thumbnail}."""
    if not isinstance(obj, dict):
        return None
    out = {"original": image_link(obj.get("fullRes")), "thumbnail": image_link(obj.get("thumbnail"))}
    return out if out["original"] else None


def esrb_rating(obj):
    src = (obj or {}).get("imageSrc") if isinstance(obj, dict) else None
    match = _ESRB_RE.search(src or "")
    if not match:
        return None
    code = match.group(1).lower()
    return _ESRB.get(code, code.upper())


# ---- reference entities ------------------------------------------------------

def platform(p):
    if not isinstance(p, dict):
        return None
    out = {"id": to_int(p.get("id")), "name": clean(p.get("name")), "short_name": clean(p.get("shortName"))}
    if "releaseDate" in p:
        out["release_date"] = iso_date(p.get("releaseDate"))
    if "imageSrcV2" in p:
        out["image"] = image_link(p.get("imageSrcV2"))
    return out


def platforms(values):
    return [x for x in (platform(p) for p in values or []) if x] or None


def genre(g):
    if not isinstance(g, dict):
        return None
    return {"id": to_int(g.get("id")), "name": clean(g.get("name"))}


def genres(values):
    return [x for x in (genre(g) for g in values or []) if x] or None


def tag(t):
    if not isinstance(t, dict):
        return None
    out = {"id": clean(t.get("tagId")), "name": clean(t.get("name"))}
    if "description" in t:
        out["description"] = clean(t.get("description"))
    if "displayOnFilter" in t:
        out["is_filterable"] = bool(t.get("displayOnFilter"))
        out["is_active"] = bool(t.get("isActive"))
    return out


def tags(values, tag_index=None):
    """Tag objects, or Mongo ids resolved through `tag_index`
    ({mongo id: tag dict}); unresolved ids are dropped."""
    out = []
    for t in values or []:
        if isinstance(t, dict):
            item = tag(t)
        elif isinstance(t, str) and tag_index:
            item = tag_index.get(t)
        else:
            item = None
        if item:
            ref = {"id": item.get("id"), "name": item.get("name")}
            if ref not in out:
                out.append(ref)
    return out or None


def score_format(f):
    if not isinstance(f, dict):
        return None
    return {
        "id": to_int(f.get("id")),
        "name": clean(f.get("name")),
        "short_name": clean(f.get("shortName")),
        "display_suffix": clean(f.get("scoreDisplay")),
        "base": to_int(f.get("base")),
        "decimals": to_int(f.get("numDecimals")),
        "is_numeric": bool(f.get("isNumeric")),
        "is_stars": bool(f.get("isStars")),
        "is_select": bool(f.get("isSelect")),
        "options": clean(f.get("options")),
    }


def company_groups(values):
    out = {"developers": None, "publishers": None}
    for c in values or []:
        if not isinstance(c, dict):
            continue
        key = _COMPANY_TYPES.get(str(c.get("type") or "").upper())
        name = clean(c.get("name"))
        if key and name:
            out[key] = (out[key] or []) + [name] if name not in (out[key] or []) else out[key]
    return out


# ---- games -----------------------------------------------------------------------

def _game_identity(g):
    gid = to_int(g.get("id"))
    name = clean(g.get("name"))
    return {"id": gid, "name": name, "link": clean(g.get("url")) or refs.game_link(gid, name)}


def game_ref(g):
    """{id, name} reference (review.game, article.relatedGames, sequence data)."""
    if not isinstance(g, dict):
        return None
    out = _game_identity(g)
    if "firstReleaseDate" in g:
        out["release_date"] = iso_date(g.get("firstReleaseDate"))
    return out


def game_card(g, tag_index=None):
    """The list-row shape (browse, popular, upcoming, hall of fame, …)."""
    if not isinstance(g, dict):
        return None
    gid = to_int(g.get("id"))
    out = _game_identity(g)
    out.update({
        "release_date": iso_date(g.get("firstReleaseDate")),
        "tier": clean(g.get("tier")),
        "top_critic_score": score(g.get("topCriticScore")),
        "percent_recommended": percent(g.get("percentRecommended")) if "percentRecommended" in g else None,
        "review_count": to_int(g.get("numReviews")),
        "platforms": platforms(g.get("Platforms")),
        "genres": genres(g.get("Genres")),
        "tags": tags(g.get("tags"), tag_index),
        "images": images(g.get("images"), gid),
    })
    if "recentReviewCount" in g:
        out["recent_review_count"] = to_int(g.get("recentReviewCount"))
    return out


def deal_card(g, tag_index=None):
    out = game_card(g, tag_index)
    deal = g.get("featuredDeal") if isinstance(g.get("featuredDeal"), dict) else {}
    out["biggest_discount_percent"] = fraction_percent(g.get("biggestDiscountPercentage"))
    out["featured_deal"] = store(deal) if deal else None
    return out


def store(a):
    """An Affiliates / featuredDeal row: store name, link, prices (USD)."""
    if not isinstance(a, dict):
        return None
    price = to_float(a.get("price"))
    base = to_float(a.get("basePrice"))
    discount = to_int(a.get("percentageOff"))
    if discount is None and price is not None and base:
        discount = round((1 - price / base) * 100) if base > price else 0
    return {
        "store": clean(a.get("name")),
        "link": clean(a.get("externalUrl")),
        "price": price,
        "base_price": base,
        "currency": "USD" if price is not None or base is not None else None,
        "discount_percent": discount,
    }


def trailer(t):
    if not isinstance(t, dict):
        return None
    video_id = clean(t.get("videoId"))
    special = clean(t.get("isSpecial"))
    return {
        "title": clean(t.get("title")),
        "link": clean(t.get("externalUrl")) or (f"https://www.youtube.com/watch?v={video_id}" if video_id else None),
        "youtube_video_id": video_id,
        "type": clean(t.get("specialName")) or (special.title() if special and special != "NO" else None),
        "description": clean(t.get("description")),
        "published_at": iso_datetime(t.get("publishedDate")),
        "channel": {"id": clean(t.get("channelId")), "name": clean(t.get("channelTitle"))},
        "is_official_opencritic": bool(t.get("isOpenCritic")),
    }


def youtube_channel(c):
    if not isinstance(c, dict):
        return None
    cid = clean(c.get("channelId"))
    return {"id": cid, "name": clean(c.get("channelTitle")) or clean(c.get("title")),
            "link": clean(c.get("externalUrl")) or (f"https://www.youtube.com/channel/{cid}" if cid else None),
            "description": clean(c.get("description"))}


def review_summary(s):
    """The editorial three-slot summary some games carry."""
    if not isinstance(s, dict) or not clean(s.get("summary")):
        return None
    points = []
    for n in (1, 2, 3):
        text = clean(s.get(f"slot{n}"))
        if text:
            points.append({"text": text, "sentiment": clean(s.get(f"slot{n}State"))})
    return {"summary": clean(s.get("summary")), "points": points or None}


def game_details(g, tag_index=None):
    if not isinstance(g, dict):
        return None
    gid = to_int(g.get("id"))
    out = _game_identity(g)
    companies = company_groups(g.get("Companies"))
    monetization = g.get("monetizationFeatures") if isinstance(g.get("monetizationFeatures"), dict) else {}
    out.update({
        "description": clean(g.get("description")),
        "release_date": iso_date(g.get("firstReleaseDate")),
        "tier": clean(g.get("tier")),
        "top_critic_score": score(g.get("topCriticScore")),
        "median_score": score(g.get("medianScore")),
        "average_score": score(g.get("averageScore")) if "averageScore" in g else None,
        "percentile": to_int(g.get("percentile")) if to_int(g.get("percentile")) not in (None, -1) else None,
        "percent_recommended": percent(g.get("percentRecommended")),
        "review_count": to_int(g.get("numReviews")),
        "top_critic_review_count": to_int(g.get("numTopCriticReviews")),
        "user_review_count": to_int(g.get("numUserReviews")),
        "is_major_title": bool(g.get("isMajorTitle")),
        "is_pre_2015": bool(g.get("isPre2015")),
        "has_loot_boxes": bool(g.get("hasLootBoxes") or monetization.get("hasLootBoxes")),
        "esrb_rating": esrb_rating(g.get("Rating")),
        "steam_id": clean(g.get("steamId")),
        "developers": companies["developers"],
        "publishers": companies["publishers"],
        "platforms": platforms(g.get("Platforms")),
        "genres": genres(g.get("Genres")),
        "tags": tags(g.get("tags"), tag_index),
        "review_summary": review_summary(g.get("reviewSummary")),
        "stores": [s for s in (store(a) for a in g.get("Affiliates") or []) if s] or None,
        "deals": {"biggest_discount_percent": fraction_percent(g.get("biggestDiscountPercentage")),
                  "biggest_discount_amount": to_float(g.get("biggestDiscountDollars")) or None,
                  "currency": "USD"},
        "images": images(g.get("images"), gid),
        "legacy_images": {
            "masthead": legacy_image(g.get("mastheadScreenshot")),
            "banner": legacy_image(g.get("bannerScreenshot")),
            "logo": legacy_image(g.get("logoScreenshot")),
            "vertical_logo": legacy_image(g.get("verticalLogoScreenshot")),
            "square": legacy_image(g.get("squareScreenshot")),
            "screenshots": [s for s in (legacy_image(x) for x in g.get("screenshots") or []) if s] or None,
        },
        "trailers": [t for t in (trailer(x) for x in g.get("trailers") or []) if t] or None,
        "youtube_channel": youtube_channel(g.get("mainChannel")),
        "dates": {
            "embargo_at": iso_datetime(g.get("embargoDate")),
            "first_review": iso_date(g.get("firstReviewDate")),
            "tenth_review": iso_date(g.get("tenthReviewDate")),
            "critical_mass_review": iso_date(g.get("criticalReviewDate")),
            "latest_review": iso_date(g.get("latestReviewDate")),
        },
        "created_at": iso_datetime(g.get("createdAt")),
        "updated_at": iso_datetime(g.get("updatedAt")),
    })
    if not any(out["legacy_images"].values()):
        out["legacy_images"] = None
    return out


# ---- reviews ---------------------------------------------------------------------

def outlet_ref(o):
    if not isinstance(o, dict):
        return None
    oid = to_int(o.get("id"))
    name = clean(o.get("name"))
    out = {"id": oid, "name": name, "link": refs.outlet_link(oid, name)}
    if "imageSrc" in o:
        out["image"] = image_set(o.get("imageSrc"))
    if "isContributor" in o:
        out["is_contributor"] = bool(o.get("isContributor"))
    return out


def author_ref(a):
    if not isinstance(a, dict):
        return None
    aid = to_int(a.get("id"))
    name = clean(a.get("name"))
    return {"id": aid, "name": name, "link": refs.critic_link(aid, name) if aid else None,
            "image": image_set(a.get("imageSrc")) if a.get("image") else None}


def has_verdict(fmt):
    """False for the "No Verdict" format (id 30: neither numeric nor a
    select scale), whose stored 0 is a placeholder, not a rating."""
    if not isinstance(fmt, dict):
        return True
    return bool(fmt.get("isNumeric") or fmt.get("isSelect"))


def outlet_scale_score(value, fmt):
    """OpenCritic stores every score on 0-100; `base` is the divisor back to
    the outlet's own scale (5-star formats: base 20 -> 90 = 4.5 stars)."""
    if value is None or not isinstance(fmt, dict) or not fmt.get("isNumeric"):
        return None
    base = to_float(fmt.get("base"), None)
    if not base:
        return None
    decimals = to_int(fmt.get("numDecimals"))
    return round(value / base, decimals if decimals is not None else 2)


def review(r):
    if not isinstance(r, dict):
        return None
    fmt = r.get("ScoreFormat")
    verdict = has_verdict(fmt)
    value = score(r.get("score")) if verdict else None
    authors = [x for x in (author_ref(a) for a in r.get("Authors") or []) if x]
    alias = clean(r.get("alias"))
    if not authors and alias:
        authors = [{"id": None, "name": alias, "link": None, "image": None}]
    hidden = bool(r.get("hideReviewUrl"))
    video_id = clean(r.get("youtubeVideoId"))
    return {
        "id": clean(r.get("_id")),
        "title": clean(r.get("title")),
        "link": None if hidden else clean(r.get("externalUrl")),
        "snippet": clean(r.get("snippet")),
        "language": clean(r.get("language")),
        "published_at": iso_date(r.get("publishedDate")),
        "score": value,
        "outlet_score": outlet_scale_score(value, fmt),
        "normalized_score": score(r.get("npScore")) if verdict else None,
        "has_verdict": verdict,
        "score_format": score_format(fmt),
        "median_score_at_review": score(r.get("medianAtTimeOfReview")),
        "is_featured": bool(r.get("isChosen")),
        "has_recommendation_override": bool(r.get("overrideRecommendation")),
        "is_video": bool(r.get("isYoutube") or video_id),
        "youtube_video_id": video_id,
        "platforms": platforms(r.get("Platforms")),
        "authors": authors or None,
        "outlet": outlet_ref(r.get("Outlet")),
        "game": game_ref(r.get("game")),
    }


def reviews(values):
    return [x for x in (review(r) for r in values or []) if x]


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else round((ordered[mid - 1] + ordered[mid]) / 2, 2)


def score_distribution(values, game=None):
    """Score histogram over a full review list (what the site's charts page
    draws client-side): per-score counts, 5-point buckets and tier shares."""
    rows = [r for r in values or [] if isinstance(r, dict)]
    rated = [r for r in rows if has_verdict(r.get("ScoreFormat"))]
    scores = [int(round(s)) for s in (score(r.get("score")) for r in rated) if s is not None]
    counts = {}
    for s in scores:
        counts[s] = counts.get(s, 0) + 1
    buckets = []
    for low in range(0, 100, 5):
        high = low + 4 if low < 95 else 100
        n = sum(c for s, c in counts.items() if low <= s <= high)
        buckets.append({"range": f"{low}-{high}", "min": low, "max": high, "count": n})
    unscored = len(rows) - len(scores)
    recommended = [r for r in rated if score(r.get("npScore")) is not None]
    return {
        "review_count": len(rows),
        "scored_review_count": len(scores),
        "unscored_review_count": unscored,
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "median_score": _median(scores),
        "recommended_share_percent": round(100 * sum(1 for r in recommended if score(r.get("npScore")) >= 100)
                                           / len(recommended), 2) if recommended else None,
        "scores": [{"score": s, "count": counts[s]} for s in sorted(counts)],
        "buckets": buckets,
    }


# ---- outlets / critics -----------------------------------------------------------

def outlet(o):
    if not isinstance(o, dict):
        return None
    oid = to_int(o.get("id"))
    name = clean(o.get("name"))
    return {
        "id": oid,
        "name": name,
        "link": refs.outlet_link(oid, name),
        "website": None if o.get("hidePublicationUrls") else clean(o.get("externalUrl")),
        "domain": clean(o.get("domain")),
        "language": clean(o.get("language")),
        "image": image_set(o.get("imageSrc")),
        "is_contributor": bool(o.get("isContributor")),
        "is_aggregated": bool(o.get("isAggregated")),
        "is_aggregated_by_opencritic": bool(o.get("isAggregatedByOpenCritic")),
        "score_format": score_format(o.get("ScoreFormat")),
        "review_count": to_int(o.get("numReviews")),
        "median_score": score(o.get("medianScore")),
        "average_score": score(o.get("averageScore")),
        "percent_recommended": percent(o.get("percentRecommended")),
        "recommended_cutoff": score(o.get("recommendedCutoff")),
        "uses_fixed_cutoff": bool(o.get("usesFixedCutoff")),
        "updated_at": iso_datetime(o.get("updatedAt")),
    }


def critic(a):
    if not isinstance(a, dict):
        return None
    aid = to_int(a.get("id"))
    name = clean(a.get("name"))
    linkedin = clean(a.get("linkedIn"))
    return {
        "id": aid,
        "name": name,
        "link": refs.critic_link(aid, name),
        "image": image_set(a.get("imageSrc")) if a.get("image") else None,
        "bio": clean(a.get("bio")),
        "hometown": clean(a.get("hometown")),
        "website": clean(a.get("externalUrl")),
        "email": clean(a.get("publicEmail")),
        "socials": {
            "twitter": clean(a.get("twitter")),
            "facebook": clean(a.get("facebook")),
            "linkedin": (f"https://www.linkedin.com/in/{linkedin.strip('/')}" if linkedin and "://" not in linkedin
                         else linkedin),
            "steam": clean(a.get("steam")),
            "xbox_live": clean(a.get("xboxLive")),
            "psn": clean(a.get("psn")),
            "nintendo_friend_code": clean(a.get("nintendoFriendCode")),
        },
        "favorite_games": [clean(g) for g in a.get("favoriteGames") or [] if clean(g)] or None,
        "is_claimed": bool(a.get("claimed")),
        "review_count": to_int(a.get("numReviews")),
        "median_score": score(a.get("medianScore")),
        "average_score": score(a.get("averageScore")),
        "percent_recommended": percent(a.get("percentRecommended")),
        "created_at": iso_datetime(a.get("createdAt")),
        "updated_at": iso_datetime(a.get("updatedAt")),
    }


def search_hit(h, kind=None):
    """Trigram search rows: {id, name, dist, relation?} -> typed hit with a
    0-1 `match` score (1 = exact)."""
    if not isinstance(h, dict):
        return None
    kind = kind or {"outlet": "outlet", "author": "critic", "critic": "critic", "game": "game"}.get(str(h.get("relation") or "").lower())
    hid = to_int(h.get("id"))
    name = clean(h.get("name"))
    link = {"game": refs.game_link, "outlet": refs.outlet_link, "critic": refs.critic_link}.get(kind)
    dist = to_float(h.get("dist"), 4)
    return {"type": kind, "id": hid, "name": name, "link": link(hid, name) if link else None,
            "match": round(1 - dist, 4) if dist is not None else None}


# ---- news ---------------------------------------------------------------------

def article(a, with_body=False):
    if not isinstance(a, dict):
        return None
    aid = to_int(a.get("id"))
    title = clean(a.get("title"))
    teaser = clean(a.get("teaser"))
    description = clean(a.get("description"))
    authors = [clean(x.get("name")) if isinstance(x, dict) else clean(x) for x in a.get("Authors") or []]
    authors = [x for x in authors if x]
    out = {
        "id": aid,
        "title": title,
        "link": refs.article_link(aid, title),
        "source_link": clean(a.get("originalUrl")),
        "type": (clean(a.get("type")) or "").lower() or None,
        "outlet": outlet_ref(a.get("Outlet")),
        "authors": authors or ([clean(a.get("syndicatedAuthor"))] if clean(a.get("syndicatedAuthor")) else None),
        "published_at": iso_datetime(a.get("publishedDate")),
        "teaser": teaser,
        "description": description if description and description != teaser else None,
        "image": image_set(a.get("imageV2")),
        "related_games": [g for g in (game_ref(x) for x in a.get("relatedGames") or []) if g] or None,
    }
    if with_body:
        out["body_html"] = clean(a.get("html"))
        out["body_text"] = strip_html(a.get("html"))
        out["created_at"] = iso_datetime(a.get("createdAt"))
        out["updated_at"] = iso_datetime(a.get("updatedAt"))
    return out


# ---- calendar / collections / community -------------------------------------------

def calendar_game(g):
    if not isinstance(g, dict):
        return None
    gid = to_int(g.get("id"))
    out = _game_identity(g)
    out["release_date"] = iso_date(g.get("firstReleaseDate"))
    out["images"] = images(g.get("images"), gid)
    return out


def calendar_event(e):
    if not isinstance(e, dict):
        return None
    return {"type": (clean(e.get("type")) or "").lower() or None, "name": clean(e.get("name")) or clean(e.get("title")),
            "start_date": iso_date(e.get("startDate") or e.get("date")), "end_date": iso_date(e.get("endDate")),
            "link": clean(e.get("externalUrl")) or clean(e.get("url"))}


def collection_summary(s):
    if not isinstance(s, dict):
        return None
    return {"key": clean(s.get("key")), "name": clean(s.get("label"))}


def collection(s):
    if not isinstance(s, dict):
        return None
    metrics = s.get("metrics") if isinstance(s.get("metrics"), dict) else {}
    return {
        "key": clean(s.get("key")),
        "name": clean(s.get("label")),
        "description": strip_html(s.get("description")),
        "description_html": clean(s.get("description")),
        "categories": [clean(c) for c in s.get("categories") or [] if clean(c)] or None,
        "game_count": to_int(metrics.get("numGames")),
        "tier_counts": {"mighty": to_int(metrics.get("mighty")), "strong": to_int(metrics.get("strong")),
                        "fair": to_int(metrics.get("fair")), "weak": to_int(metrics.get("weak")),
                        "not_rated": to_int(metrics.get("notRated")),
                        "not_on_opencritic": to_int(metrics.get("notOnOpenCritic"))},
        "recent_count": to_int(metrics.get("recent")),
        "games": [g for g in (game_ref(x) for x in s.get("data") or []) if g] or None,
        "games_not_on_opencritic": [{"name": clean(g.get("name")), "release_date": iso_date(g.get("releaseDate") or g.get("firstReleaseDate"))}
                                    for g in s.get("gamesNotOnOpenCritic") or [] if isinstance(g, dict) and clean(g.get("name"))] or None,
        "created_at": iso_datetime(s.get("createdAt")),
        "updated_at": iso_datetime(s.get("updatedAt")),
    }


def user_rating_summary(r, game_id=None):
    if not isinstance(r, dict):
        return {"median_score": None, "rating_count": None}
    return {"median_score": score(r.get("median")), "rating_count": to_int(r.get("count"))}


def user_review(r):
    if not isinstance(r, dict):
        return None
    user = r.get("user") if isinstance(r.get("user"), dict) else {}
    slug = clean(user.get("slug"))
    return {
        "id": clean(r.get("id")) or clean(r.get("_id")),
        "user": {"id": to_int(user.get("id")) or to_int(r.get("userId")), "name": clean(user.get("displayName")),
                 "slug": slug, "link": refs.user_link(slug)},
        "score": score(r.get("score")),
        "score_format_id": to_int(r.get("scoreFormat")),
        "is_recommended": bool(r.get("recommend")),
        "recommend_to": [clean(x) for x in r.get("recommendTo") or [] if clean(x)] or None,
        "excerpt": clean(r.get("excerpt")),
        "status": clean(r.get("status")),
        "created_at": iso_datetime(r.get("createdAt")),
        "updated_at": iso_datetime(r.get("updatedAt")),
    }


# ---- pagination --------------------------------------------------------------------

def pagination(page, per_page, total_count=None, has_more=False):
    """The block route_glue.paginate() lifts into the flat gateway shape."""
    if total_count is not None and per_page:
        total_pages = max((int(total_count) + int(per_page) - 1) // int(per_page), 1)
    else:
        total_pages = page + 1 if has_more else page
    return {"page": page, "items_per_page": per_page, "total_pages": total_pages, "total_count": total_count}
