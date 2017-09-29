# -*- coding: utf-8 -*-
from __future__ import absolute_import

import warnings

from .exceptions import *  # NOQA

from .version import get_git_version

# monkey patch django's json field to get around django/django#6929 on
# django <1.11
import django
try:
    django_version_major_minor = list(
        map(int, django.__version__.split('.')[:2]))
except ValueError:
    msg = ("Failed to determine Django version. Django's json field will not "
           "be patched (django/django#6929).")
    warnings.warn(msg)
else:
    if django_version_major_minor < [1, 11]:
        import django.contrib.postgres.fields.jsonb

        django.contrib.postgres.fields.jsonb.KeyTransform._as_sql_original = \
            django.contrib.postgres.fields.jsonb.KeyTransform.as_sql

        def as_sql(self, *args, **kwargs):
            _as_sql = self._as_sql_original(*args, **kwargs)
            return '({})'.format(_as_sql[0]), _as_sql[1]

        django.contrib.postgres.fields.jsonb.KeyTransform.as_sql = as_sql

__version__ = get_git_version()
__all__ = ['__version__']
