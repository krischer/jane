# -*- coding: utf-8 -*-
import io

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from lxml import etree
from lxml.builder import E

from jane.documents.models import DocumentIndex
from jane.fdsnws.event_query import query_event
from jane.fdsnws.views.utils import fdnsws_error, parse_query_parameters

import obspy


VERSION = '1.1.1'
QUERY_TIMEOUT = 10


def utc_to_timestamp(value):
    return obspy.UTCDateTime(value).timestamp


QUERY_PARAMETERS = {
    "starttime": {
        "aliases": ["starttime", "start"],
        "type": utc_to_timestamp,
        "required": False,
        "default": None
    },
    "endtime": {
        "aliases": ["endtime", "end"],
        "type": utc_to_timestamp,
        "required": False,
        "default": None
    },
    "minlatitude": {
        "aliases": ["minlatitude", "minlat"],
        "type": float,
        "required": False,
        "default": None
    },
    "maxlatitude": {
        "aliases": ["maxlatitude", "maxlat"],
        "type": float,
        "required": False,
        "default": None
    },
    "minlongitude": {
        "aliases": ["minlongitude", "minlon"],
        "type": float,
        "required": False,
        "default": None
    },
    "maxlongitude": {
        "aliases": ["maxlongitude", "maxlon"],
        "type": float,
        "required": False,
        "default": None
    },
    "latitude": {
        "aliases": ["latitude", "lat"],
        "type": float,
        "required": False,
        "default": None
    },
    "longitude": {
        "aliases": ["longitude", "lon"],
        "type": float,
        "required": False,
        "default": None
    },
    "minradius": {
        "aliases": ["minradius"],
        "type": float,
        "required": False,
        "default": 0.0
    },
    "maxradius": {
        "aliases": ["maxradius"],
        "type": float,
        "required": False,
        "default": None
    },
    "mindepth": {
        "aliases": ["mindepth"],
        "type": float,
        "required": False,
        "default": None
    },
    "maxdepth": {
        "aliases": ["maxdepth"],
        "type": float,
        "required": False,
        "default": None
    },
    "minmagnitude": {
        "aliases": ["minmagnitude", "minmag"],
        "type": float,
        "required": False,
        "default": None
    },
    "maxmagnitude": {
        "aliases": ["maxmagnitude", "maxmag"],
        "type": float,
        "required": False,
        "default": None
    },
    "orderby": {
        "aliases": ["orderby"],
        "type": str,
        "required": False,
        "default": "time"},
    "nodata": {
        "aliases": ["nodata"],
        "type": int,
        "required": False,
        "default": 204},
    "format": {
        "aliases": ["format"],
        "type": str,
        "required": False,
        "default": "xml"},
}


def _error(request, message, status_code=400):
    return fdnsws_error(request, status_code=status_code, service="event",
                        message=message, version=VERSION)


def index(request):
    """
    FDSNWS event Web Service HTML index page.
    """
    options = {
        'host': request.build_absolute_uri('/')[:-1],
        'instance_name': settings.JANE_INSTANCE_NAME,
        'accent_color': settings.JANE_ACCENT_COLOR
    }
    return render_to_response("fdsnws/event/1/index.html", options,
                              RequestContext(request))


def version(request):  # @UnusedVariable
    """
    Returns full service version in plain text.
    """
    return HttpResponse(VERSION, content_type="text/plain")


def wadl(request):  # @UnusedVariable
    """
    Return WADL document for this application.
    """
    options = {
        'host': request.build_absolute_uri('/')
    }
    return render_to_response("fdsnws/event/1/application.wadl", options,
                              RequestContext(request),
                              content_type="application/xml; charset=utf-8")


def query(request):
    """
    Parses and returns event request
    """
    # handle both: HTTP POST and HTTP GET variables
    params = parse_query_parameters(QUERY_PARAMETERS,
                                    getattr(request, request.method))

    # A returned string is interpreted as an error message.
    if isinstance(params, str):
        return _error(request, params, status_code=400)

    if params.get("starttime") and params.get("endtime") and (
            params.get("endtime") <= params.get("starttime")):
        return _error(request, 'Start time must be before end time')

    if params.get("latitude") is not None or \
            params.get("longitude") is not None or \
            params.get("maxradius") is not None:
        if params.get("longitude") is None:
            return _error(request, "'longitude' must also be given for "
                                   "radial queries.", status_code=400)
        if params.get("latitude") is None:
            return _error(request, "'latitude' must also be given for "
                                   "radial queries.", status_code=400)
        if params.get("maxradius") is None:
            return _error(request, "'maxradius' must also be given for "
                                   "radial queries.", status_code=400)

    if params.get("nodata") not in [204, 404]:
        return _error(request, "nodata must be '204' or '404'.",
                      status_code=400)

    if params.get("format") not in ["xml", "text"]:
        return _error(request, "format must be 'xml' or 'text'.",
                      status_code=400)

    with io.BytesIO() as fh:
        status = query_event(fh, **params)
        fh.seek(0, 0)

        if status == 200:
            response = HttpResponse(fh, content_type='text/xml')
            return response
        else:
            msg = 'Not Found: No data selected'
            return _error(request, msg, status)


@login_required
def queryauth(request):
    """
    Parses and returns data request
    """
    return query(request)


def contributors(request):  # @UnusedVariable
    """
    Returns a list of contributors as an XML string.
    """
    values = DocumentIndex.objects.get_distinct_values(
        document_type="quakeml",
        json_key="agency")

    xml = E.Contributors(
        E.total(str(len(values))),
        *[E.Contributor(_i) for _i in values]
    )

    with io.BytesIO() as fh:
        etree.ElementTree(xml).write(fh, pretty_print=True,
                                     encoding="utf-8",
                                     xml_declaration=True)
        fh.seek(0, 0)

        return HttpResponse(fh, content_type="text/xml")
