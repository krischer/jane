# -*- coding: utf-8 -*-
from django.shortcuts import get_object_or_404
from django.http.response import Http404

import obspy

import jane
from jane.documents import models


# Cache the plugin metainformation to only have to retrieve it once.
PLUGIN_META_CACHE = {}
for plugin in jane.documents.plugins.IndexerPluginPoint.get_plugins():
    if not plugin.is_active():
        continue
    plugin = plugin.get_plugin()
    PLUGIN_META_CACHE[plugin.name] = plugin.meta


def get_document_index_queryset(document_type, query_params):
    """
    Helper function returning a queryset by searching over the JSON indices.

    :param document_type: The document type to query.
    :param query_params: Any additional query parameters.

    The available search parameters depend on the type.

    * String can have wildcards, e.g.
        `...&author=ja*&...`
    * Ints/Floats can either be searched for equality
        `...&magnitude=7.2&...`
      or minimum and maximum values
        `...&min_magnitude=5&max_magnitude=7&...`
    * Same for obspy.UTCDateTime objects.
        `...&origin_time=2012-01-02&...`
        `...&min_origin_time=2012-01-02&max_origin_time=2013-01-01&...`
    * Booleans can only be searched for equality.
        `...&public=True&...`
    """
    try:
        meta = PLUGIN_META_CACHE[document_type]
    except KeyError:
        raise Http404

    res_type = get_object_or_404(models.DocumentType, name=document_type)

    queryset = models.DocumentIndex.objects. \
        filter(document__document_type=res_type)

    # In many cases there will be nothing to do.
    if not query_params:
        return queryset

    # Filter based on the attributes in the meta field.
    where = []

    for key, value in meta.items():
        value_type = value["type"]
        # Handle strings.
        if value_type is str:
            if key in query_params:
                value = query_params.get(key)
                # Possible wildcards.
                if "*" in value or "?" in value:
                    value = value.replace("?", "_").replace("*", r"%%")
                    # PostgreSQL specific case insensitive LIKE statement.
                    where.append("json->>'%s' ILIKE '%s'" % (key, value))
                else:
                    where.append(_get_json_query(key, "=", value_type, value))
        # Handle integers and floats.
        elif value_type in (int, float, obspy.UTCDateTime):
            choices = ("min_%s", ">="), ("max_%s", "<="), ("%s", "=")
            for name, operator in choices:
                name = name % key
                if name not in query_params:
                    continue
                where.append(_get_json_query(
                    key, operator, value_type,
                    value_type(query_params.get(name))))
        # Handle bools.
        elif value_type is bool:
            if key in query_params:
                value = query_params.get(key).lower()
                if value in ["t", "true", "yes", "y"]:
                    value = True
                elif value in ["f", "false", "no", "n"]:
                    value = False
                else:
                    raise NotImplementedError
                where.append(_get_json_query(key, "=", bool, value))

    queryset = queryset.extra(where=where)
    return queryset


JSON_QUERY_TEMPLATE_MAP = {
    int: "CAST(json->>'%s' AS INTEGER) %s %s",
    float: "CAST(json->>'%s' AS REAL) %s %s",
    str: "LOWER(json->>'%s') %s LOWER('%s')",
    obspy.UTCDateTime: "CAST(json->>'%s' AS TIMESTAMP) %s TIMESTAMP '%s'"
}


def _get_json_query(key, operator, type, value):
    return JSON_QUERY_TEMPLATE_MAP[type] % (key, operator, str(value))
