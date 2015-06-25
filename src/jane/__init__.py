# -*- coding: utf-8 -*-
from __future__ import absolute_import

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app  # NOQA
from .exceptions import *  # NOQA

from .version import get_git_version

__version__ = get_git_version()
