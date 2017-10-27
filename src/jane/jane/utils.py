# -*- coding: utf-8 -*-
from rest_framework.routers import SimpleRouter


class OptionalTrailingSlashSimpleRouter(SimpleRouter):
    """
    Router that does not care if there is a leading slash or not.

    The URLs in the hyperlinked fields will use the value given during the
    init but the actual API will work with both.

    Does not appear to have any downsides and it pretty nice to work with.

    Based on a discussion in
    https://github.com/tomchristie/django-rest-framework/issues/905
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = "/?"


def _queryset_filter_jsonfield_isnull(queryset, path, isnull, field='json'):
    """
    Replaces the buggy isnull query on json fields, see
    https://stackoverflow.com/q/38528516

    :type queryset: :class:`django.db.models.query.QuerySet`
    :param queryset: Django queryset object to do the query on.
    :type field: str
    :param field: Name of the field (column) in the databse table that holds
        the json data for the query. By default should always be "json" for
        Jane.
    :type path: list
    :param path: List of field names as strings to traverse in the json field.
        For example use ``field='json', path=['end_date'], isnull=True``, for a
        query of type ``queryset.filter(json__end_date__isnull=True)``.
    :type isnull: bool
    :param isnull: Whether to return items with the respective field being
        `null` (``isnull=True``) or it *not* being `null` (``isnull=False``).
    """
    key = '__'.join([field] + list(path[:-1]) + ['contains'])
    if not path:
        raise ValueError()
    kwargs = {key: {path[-1]: None}}
    if isnull:
        method = queryset.filter
    else:
        method = queryset.exclude
    return method(**kwargs)
