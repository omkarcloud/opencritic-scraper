"""OpenCritic outlets (publications): the full directory with local
filtering, and one outlet's profile."""
from opencritic import fetch
from opencritic import parsers as P
from opencritic.shared import paged_result

LIST_PAGE_SIZE = 50
OUTLET_SORTS = ("review-count", "name", "median-score", "percent-recommended")


def list_outlets(page=1, limit=LIST_PAGE_SIZE, query=None, language=None, contributors_only=None,
                 sort="review-count"):
    """Every outlet OpenCritic aggregates (~830), optionally narrowed by a
    name / domain substring, review language (en-us, de-de, …) or
    contributor status, sorted by review count / name / median score."""
    rows = [o for o in (P.outlet(r) for r in fetch.api_get("outlet") or []) if o]
    if query:
        q = query.lower()
        rows = [o for o in rows if q in (o["name"] or "").lower() or q in (o["domain"] or "").lower()]
    if language:
        rows = [o for o in rows if (o["language"] or "").lower() == language.lower()]
    if contributors_only:
        rows = [o for o in rows if o["is_contributor"]]
    keys = {"review-count": lambda o: -(o["review_count"] or 0),
            "name": lambda o: (o["name"] or "").lower(),
            "median-score": lambda o: -(o["median_score"] or 0),
            "percent-recommended": lambda o: -(o["percent_recommended"] or 0)}
    rows.sort(key=keys[sort])
    start = (page - 1) * limit
    return paged_result("results", rows[start:start + limit], page, limit, len(rows),
                        filters={"query": query, "language": language,
                                 "contributors_only": bool(contributors_only), "sort": sort})


def details(outlet):
    """An outlet's profile: score format, review count, median / average
    score, percent recommended and its recommendation cutoff."""
    return P.outlet(fetch.api_get(f"outlet/{outlet}", not_found=f"outlet {outlet}"))
