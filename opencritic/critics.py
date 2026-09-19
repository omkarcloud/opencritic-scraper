"""OpenCritic critics (authors): search by name and one critic's profile."""
from opencritic import fetch
from opencritic import parsers as P


def search(query):
    """Critics whose name is close to `query` (trigram similarity). 10 hits."""
    rows = fetch.api_get("author/search", {"criteria": query})
    return {"query": query, "results": [h for h in (P.search_hit(r, "critic") for r in rows or []) if h]}


def details(critic):
    """A critic's profile: bio, hometown, socials, favourite games and
    review stats."""
    return P.critic(fetch.api_get(f"author/{critic}", not_found=f"critic {critic}"))
