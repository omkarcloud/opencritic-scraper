"""Marshmallow request schemas for every /opencritic/* route.

Generic fields live in the shared top-level schema_fields.py; this module
adds the OpenCritic resolvers and the per-route schemas. Every schema's
load() output is the kwargs dict its endpoint function takes.

ONE param per input (tripadvisor QueryOrLinkField convention, never a
sibling `url`/`id` pair): `game`, `outlet`, `critic` and `article` each
take a bare numeric id OR an opencritic.com link (refs.py); `collection`
takes the collection key.
"""
from datetime import date

from marshmallow import ValidationError, validate

from opencritic import refs
from opencritic.collections import COLLECTION_SORTS
from opencritic.community import USER_REVIEW_SORTS
from opencritic.games import BROWSE_PLATFORMS, GAME_PERIODS, GAME_SORTS, HALL_OF_FAME_FIRST_YEAR
from opencritic.outlets import OUTLET_SORTS
from opencritic.reviews import REVIEW_SORTS
from schema_fields import (BaseSchema, ChoiceField, CommaListField, Flag, PageField, PageSizeField,
                           PositiveInt, QueryField, RefField, StrippedString)


class GameRefField(RefField):
    resolver = staticmethod(lambda value: refs.resolve("game", value))


class OutletRefField(RefField):
    resolver = staticmethod(lambda value: refs.resolve("outlet", value))


class CriticRefField(RefField):
    resolver = staticmethod(lambda value: refs.resolve("critic", value))


class ArticleRefField(RefField):
    resolver = staticmethod(lambda value: refs.resolve("article", value))


class CollectionField(RefField):
    resolver = staticmethod(refs.resolve_collection)


class TagField(StrippedString):
    """A tag slug from /opencritic/tags (action, indie, souls-like, …)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("load_default", None)
        super().__init__(**kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        if value is None:
            return None
        slug = value.lower().replace(" ", "-").replace("_", "-")
        if not slug.replace("-", "").isalnum():
            raise ValidationError("Must be a tag slug such as action, indie or souls-like (see /opencritic/tags).")
        return slug


class YearField(PositiveInt):
    """A year between `first` and the current year + `ahead` (release years
    run one ahead; Hall of Fame years stop at the current year)."""

    def __init__(self, first=2000, ahead=1, **kwargs):
        self.first = first
        self.ahead = ahead
        super().__init__(**kwargs)
        self.validate = None
        self.validators = []

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        if value is None:
            return None
        last = date.today().year + self.ahead
        if not (self.first <= value <= last):
            raise ValidationError(f"Must be a year between {self.first} and {last}.")
        return value


# ---- search --------------------------------------------------------------------------

class SearchSchema(BaseSchema):
    query = QueryField(max_length=100)
    type = ChoiceField(["game", "outlet", "critic"])


class QuerySchema(BaseSchema):
    query = QueryField(max_length=100)


# ---- games -----------------------------------------------------------------------------

class GameSchema(BaseSchema):
    game = GameRefField()


class GameBrowseSchema(BaseSchema):
    page = PageField(max_page=500)
    platforms = CommaListField(allowed=list(BROWSE_PLATFORMS), upper=False, max_items=14)
    period = ChoiceField(list(GAME_PERIODS), load_default="all-time")
    year = YearField(first=1990)
    tag = TagField()
    sort = ChoiceField(list(GAME_SORTS), load_default="score")
    order = ChoiceField(["asc", "desc"])


class GameReviewsSchema(BaseSchema):
    game = GameRefField()
    page = PageField(max_page=500)
    sort = ChoiceField(list(REVIEW_SORTS), load_default="blend")
    order = ChoiceField(["asc", "desc"])


class HallOfFameSchema(BaseSchema):
    year = YearField(first=HALL_OF_FAME_FIRST_YEAR, ahead=0)


class EmptySchema(BaseSchema):
    pass


# ---- outlets / critics -------------------------------------------------------------------

class OutletListSchema(BaseSchema):
    page = PageField(max_page=500)
    limit = PageSizeField(default=50, max_size=200)
    query = StrippedString(load_default=None, validate=validate.Length(min=1, max=100))
    language = StrippedString(load_default=None, validate=validate.Length(min=2, max=10))
    contributors_only = Flag()
    sort = ChoiceField(list(OUTLET_SORTS), load_default="review-count")


class OutletSchema(BaseSchema):
    outlet = OutletRefField()


class OutletReviewsSchema(BaseSchema):
    outlet = OutletRefField()
    page = PageField(max_page=500)
    sort = ChoiceField(list(REVIEW_SORTS), load_default="newest")
    order = ChoiceField(["asc", "desc"])


class CriticSchema(BaseSchema):
    critic = CriticRefField()


class CriticReviewsSchema(BaseSchema):
    critic = CriticRefField()
    page = PageField(max_page=500)
    sort = ChoiceField(list(REVIEW_SORTS), load_default="newest")
    order = ChoiceField(["asc", "desc"])


# ---- news / collections / community ----------------------------------------------------------

class NewsSchema(BaseSchema):
    page = PageField(max_page=5000)


class ArticleSchema(BaseSchema):
    article = ArticleRefField()


class CollectionSchema(BaseSchema):
    collection = CollectionField()


class CollectionGamesSchema(BaseSchema):
    collection = CollectionField()
    page = PageField(max_page=500)
    sort = ChoiceField(list(COLLECTION_SORTS), load_default="score")


class UserReviewsSchema(BaseSchema):
    game = GameRefField()
    page = PageField(max_page=500)
    sort = ChoiceField(list(USER_REVIEW_SORTS), load_default="score")
