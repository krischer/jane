# -*- coding: utf-8 -*-
import io

from django.conf import settings
from django.http.response import HttpResponse
from django.shortcuts import render
import obspy

from jane.jane.decorators import logged_in_or_basicauth
from jane.fdsnws.station_query import query_stations
from jane.fdsnws.views.utils import fdnsws_error, parse_query_parameters


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
    "startbefore": {
        "aliases": ["startbefore"],
        "type": utc_to_timestamp,
        "required": False,
        "default": None
    },
    "startafter": {
        "aliases": ["startafter"],
        "type": utc_to_timestamp,
        "required": False,
        "default": None
    },
    "endbefore": {
        "aliases": ["endbefore"],
        "type": utc_to_timestamp,
        "required": False,
        "default": None
    },
    "endafter": {
        "aliases": ["endafter"],
        "type": utc_to_timestamp,
        "required": False,
        "default": None
    },
    "network": {
        "aliases": ["network", "net"],
        "type": str,
        "required": False,
        "default": None
    },
    "station": {
        "aliases": ["station", "sta"],
        "type": str,
        "required": False,
        "default": None
    },
    "location": {
        "aliases": ["location", "loc"],
        "type": str,
        "required": False,
        "default": None
    },
    "channel": {
        "aliases": ["channel", "cha"],
        "type": str,
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
    "format": {
        "aliases": ["format"],
        "type": str,
        "required": False,
        "default": "xml"
    },
    "level": {
        "aliases": ["level"],
        "type": str,
        "required": False,
        "default": "station"},
    "nodata": {
        "aliases": ["nodata"],
        "type": int,
        "required": False,
        "default": 204}
}


def _error(request, message, status_code=400):
    return fdnsws_error(request, status_code=status_code, service="station",
                        message=message, version=VERSION)


def index(request):
    """
    FDSNWS station Web Service HTML index page.
    """
    context = {
        'host': request.build_absolute_uri('/')[:-1],
        'instance_name': settings.JANE_INSTANCE_NAME,
        'accent_color': settings.JANE_ACCENT_COLOR
    }
    return render(request, "fdsnws/station/1/index.html", context)


def version(request):  # @UnusedVariable
    """
    Returns full service version in plain text.
    """
    return HttpResponse(VERSION, content_type="text/plain")


def wadl(request):  # @UnusedVariable
    """
    Return WADL document for this application.
    """
    context = {
        'host': request.build_absolute_uri('/')
    }
    return render(request, "fdsnws/station/1/application.wadl", context,
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

    format = params.get("format").lower()
    if format not in ("xml", "text"):
        return _error(request, "format must be 'xml' or 'text'.",
                      status_code=400)
    params["format"] = format

    if params["format"] == "text" and params.get("level") == "response":
        return _error(request, "format='text' is not compatible with "
                               "level='response'", status_code=400)

    if params["format"] == "xml":
        content_type = "text/xml"
    elif params["format"] == "text":
        content_type = "text"
    else:
        raise NotImplementedError

    if params.get("level") not in ["network", "station", "channel",
                                   "response"]:
        return _error(request, "level must be 'network', 'station', "
                               "'channel', or 'response'", status_code=400)

    for key in ["network", "station", "location", "channel"]:
        if key not in params:
            continue
        params[key] = [_i.strip().upper() for _i in
                       params[key].replace(' ', '').split(',')]
    if "location" in params:
        params["location"] = [_i.replace('--', '')
                              for _i in params["location"]]

    # Get the url to put it into the StationXML file.
    url = request.build_absolute_uri(request.get_full_path())

    with io.BytesIO() as fh:
        status = query_stations(fh, url=url, **params)
        fh.seek(0, 0)

        if status == 200:
            response = HttpResponse(fh, content_type=content_type)
            return response
        else:
            msg = 'Not Found: No data selected'
            return _error(request, msg, status)


@logged_in_or_basicauth(settings.JANE_INSTANCE_NAME)
def queryauth(request):
    """
    Parses and returns data request
    """
    return query(request)
