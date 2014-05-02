# -*- coding: utf-8 -*-
"""
Base utilities.
"""

import datetime


def to_datetime(timestamp):
    if not timestamp:
        return None
    return datetime.datetime.fromtimestamp(float(timestamp))
