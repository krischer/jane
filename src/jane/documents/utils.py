# -*- coding: utf-8 -*-

import math


def deg2km(degrees):
    """
    Utility function converting degrees to kilometers.
    """
    radius = 6371.0
    return degrees * (2.0 * radius * math.pi / 360.0)
