# -*- coding: utf-8 -*-
import os
from celery.result import AsyncResult, TimeoutError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.servers.basehttp import FileWrapper
from django.http.response import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from rest_framework.reverse import reverse

from jane.fdsnws.tasks import query_stations
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
    options = {
        'host': request.build_absolute_uri('/')[:-1],
    }
    return render_to_response("fdsnws/station/1/index.html", options,
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
    return render_to_response("fdsnws/station/1/application.wadl", options,
                              RequestContext(request),
                              content_type="application/xml; charset=utf-8")


def query(request, debug=False):
    """
    Parses and returns event request
    """
    # handle both: HTTP POST and HTTP GET variables
    params = parse_query_parameters(QUERY_PARAMETERS, request.REQUEST)

    # A returned string is interpreted as an error message.
    if isinstance(params, str):
        return _error(request, params, status_code=400)

    if params.get("starttime") and params.get("endtime") and (
            params.get("endtime") <= params.get("starttime")):
        return _error(request, 'Start time must be before end time')

    if params.get("nodata") not in [204, 404]:
        return _error(request, "nodata must be '204' or '404'.",
                      status_code=400)

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

    # process query
    if debug:
        # direct
        status = query_stations(**params)
        task_id = 'debug'
    else:
        # using celery
        task = query_stations.delay(**params)
        task_id = task.task_id
        # check task status for QUERY_TIMEOUT seconds
        asyncresult = AsyncResult(task_id)
        try:
            status = asyncresult.get(timeout=QUERY_TIMEOUT, interval=0.5)
        except TimeoutError:
            msg = """Timeout error: request took more than %s seconds

You may check the current processing status and download your results via
%s""" % (QUERY_TIMEOUT, reverse('fdsnws_station_1_result', request=request,
                                kwargs={'task_id': task_id}))
            return _error(request, msg, 413)

    print("STATUS:", status)

    # response
    if status == 200:
        return result(request, task_id)
    else:
        msg = 'Not Found: No data selected'
        return _error(request, msg, status)


@login_required
def queryauth(request, debug=False):
    """
    Parses and returns data request
    """
    return query(request, debug=debug)


def result(request, task_id):  # @UnusedVariable
    """
    Returns requested event file
    """
    if task_id != "debug":
        asyncresult = AsyncResult(task_id)
        try:
            asyncresult.get(timeout=1.5)
        except TimeoutError:
            raise Http404()
        # check if ready
        if not asyncresult.ready():
            msg = 'Request %s not ready yet' % (task_id)
            return _error(request, msg, 413)
    # generate filename
    filename = os.path.join(settings.MEDIA_ROOT, 'fdsnws', 'stations',
                            task_id[0:2], task_id + ".xml")
    fh = FileWrapper(open(filename, 'rb'))
    response = HttpResponse(fh, content_type="text/xml")
    return response
