"""Cache TTL per /opencritic/* endpoint (cache.py, keyed on the validated
params — marshmallow fills the defaults, so `?page=1` and no `page` share a
row).

Tiers follow how fast each surface moves: the reviewed-today / this-week
lists and deals churn within the day, review lists and game scores move as
reviews land (hours), profiles and articles rarely, reference lists
(platforms / genres / tags / score formats) almost never. Upstream itself
serves everything with cache-control max-age=30.
"""
from datetime import timedelta

# --- games -------------------------------------------------------------------
GAME_CACHE = timedelta(hours=6)            # scores move as reviews land
GAME_MEDIA_CACHE = timedelta(days=3)
GAME_LIST_CACHE = timedelta(hours=6)       # browse / hall of fame
GAME_SEARCH_CACHE = timedelta(days=1)
TRENDING_CACHE = timedelta(hours=1)        # popular / reviewed today / this week
UPCOMING_CACHE = timedelta(hours=6)        # upcoming / recently released
DEALS_CACHE = timedelta(hours=3)

# --- reviews -------------------------------------------------------------------
REVIEWS_CACHE = timedelta(hours=6)
REVIEWS_ALL_CACHE = timedelta(hours=12)
SCORE_DISTRIBUTION_CACHE = timedelta(hours=12)

# --- outlets / critics -----------------------------------------------------------
OUTLET_LIST_CACHE = timedelta(days=1)
OUTLET_CACHE = timedelta(days=1)
CRITIC_CACHE = timedelta(days=1)
CRITIC_SEARCH_CACHE = timedelta(days=1)
SEARCH_CACHE = timedelta(days=1)

# --- news / calendar / collections / community -----------------------------------
NEWS_CACHE = timedelta(hours=1)
ARTICLE_CACHE = timedelta(days=7)
GAME_NEWS_CACHE = timedelta(hours=6)
CALENDAR_CACHE = timedelta(hours=6)
COLLECTIONS_CACHE = timedelta(days=1)
COLLECTION_GAMES_CACHE = timedelta(hours=12)
USER_RATING_CACHE = timedelta(hours=3)
USER_REVIEWS_CACHE = timedelta(hours=3)

# --- reference -------------------------------------------------------------------
REFERENCE_CACHE = timedelta(days=7)
