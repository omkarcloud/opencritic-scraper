"""OpenCritic reference parsing: ONE param per input that auto-detects its
forms (tripadvisor QueryOrLinkField convention — never a sibling
`url`/`id` pair). Every resolver returns a plain value so the validated
params stay usable as a response-cache key:

  game        463 | https://opencritic.com/game/463/the-witcher-3-wild-hunt
              | …/game/463/the-witcher-3-wild-hunt/reviews (any sub-page)
  outlet      56  | https://opencritic.com/outlet/56/ign
  critic      481 | https://opencritic.com/critic/481/travis-northup
  article     36879 | https://opencritic.com/news/36879/some-slug
  collection  xbox-game-pass-ultimate (the sequence key; no site link form)

Numeric ids are returned as ints, keys as lower-case slugs.
"""
import re
from urllib.parse import urlparse

_HOSTS = ("opencritic.com", "www.opencritic.com")
_PATH_SEGMENT = {"game": "game", "outlet": "outlet", "critic": "critic", "article": "news"}
_EXAMPLES = {"game": ("463", "game/463/the-witcher-3-wild-hunt"),
             "outlet": ("56", "outlet/56/ign"),
             "critic": ("481", "critic/481/travis-northup"),
             "article": ("36879", "news/36879/diablos-deckard-cain-is-officially-coming-back")}
_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,80}$")


def _error(kind):
    eid, path = _EXAMPLES[kind]
    return ValueError(f"{kind} must be an OpenCritic {kind} id (e.g. {eid}) or an "
                      f"opencritic.com/{path} link")


def parse_link(value):
    """opencritic.com link -> (kind, id) or (None, None)."""
    url = value if "://" in value else "https://" + value.lstrip("/")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in _HOSTS:
        return None, None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or not parts[1].isdigit():
        return None, None
    for kind, segment in _PATH_SEGMENT.items():
        if parts[0].lower() == segment:
            return kind, int(parts[1])
    return None, None


def resolve(kind, value):
    """Bare id or link -> int id for game/outlet/critic/article."""
    value = (value or "").strip()
    if value.isdigit():
        return int(value)
    if "opencritic.com" in value.lower() or value.startswith(("http://", "https://", "//")):
        found_kind, found_id = parse_link(value)
        if found_kind == kind:
            return found_id
    raise _error(kind)


def resolve_collection(value):
    key = (value or "").strip().lower()
    if not _KEY_RE.match(key):
        raise ValueError("collection must be an OpenCritic collection key (e.g. xbox-game-pass-ultimate)")
    return key


def slugify(name):
    """The site's `slug` pipe: drop apostrophes, every other non-alphanumeric
    run becomes one '-', lower-cased (trailing '-' kept, as on the site)."""
    if not name:
        return ""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", str(name).replace("'", ""), flags=re.I)).lower()


def game_link(game_id, name=None):
    slug = slugify(name)
    return f"https://opencritic.com/game/{game_id}/{slug}" if slug else f"https://opencritic.com/game/{game_id}"


def outlet_link(outlet_id, name=None):
    slug = slugify(name)
    return f"https://opencritic.com/outlet/{outlet_id}/{slug}" if slug else f"https://opencritic.com/outlet/{outlet_id}"


def critic_link(critic_id, name=None):
    slug = slugify(name)
    return f"https://opencritic.com/critic/{critic_id}/{slug}" if slug else f"https://opencritic.com/critic/{critic_id}"


def article_link(article_id, title=None):
    slug = slugify(title)
    return f"https://opencritic.com/news/{article_id}/{slug}" if slug else f"https://opencritic.com/news/{article_id}"


def user_link(slug):
    return f"https://opencritic.com/{slug}/ratings" if slug else None
