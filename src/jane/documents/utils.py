# -*- coding: utf-8 -*-

import math

from jsonfield.fields import JSONField


class PostgreSQLJSONBField(JSONField):
    """
    Make the JSONField use JSONB as a datatype, a typed JSON variant.
    """
    def db_type(self, connection):  # @UnusedVariable
        return "jsonb"


def deg2km(degrees):
    """
    Utility function converting degrees to kilometers.
    """
    radius = 6371.0
    return degrees * (2.0 * radius * math.pi / 360.0)
