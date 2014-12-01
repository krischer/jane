# -*- coding: utf-8 -*-

from obspy.core.utcdatetime import UTCDateTime

from celery.result import AsyncResult
from django.http.response import HttpResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from jane.fdsnws.tasks import process_query
from jane.fdsnws.views.default import fdnsws_error


VERSION = '1.1.1'
QUERY_TIMEOUT = 10


def _error(request, message, status_code=400):
    return fdnsws_error(request, status_code=status_code, message=message,
                        version=VERSION)


def index(request):
    """
    FDSNWS dataselect Web Service HTML index page.
    """
    options = {}
    return render_to_response("fdsnws/dataselect/1/index.html", options,
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
    return render_to_response("fdsnws/dataselect/1/application.wadl", options,
        RequestContext(request), content_type="application/xml; charset=utf-8")


def query(request):
    """
    Parses and returns data request
    """
    # handle both: HTTP POST and HTTP GET variables
    params = request.REQUEST
    # starttime/endtime
    starttime = params.get('starttime') or params.get('start')
    if not starttime:
        return _error(request, 'Start time must be specified')
    try:
        starttime = UTCDateTime(starttime)
    except Exception as e:
        msg = 'Error parsing starttime: %s\n\n%s' % (starttime, e)
        return _error(request, msg)
    endtime = params.get('endtime') or params.get('end') or None
    if not endtime:
        return _error(request, 'End time must be specified')
    try:
        endtime = UTCDateTime(endtime)
    except Exception as e:
        msg = 'Error parsing endtime: %s\n\n%s' % (endtime, e)
        return _error(request, msg)
    if endtime <= starttime:
        return _error(request, 'Start time must be before end time')
    # net/sta/loc/cha
    networks = params.get('network') or params.get('net') or '*'
    networks = networks.replace(' ', '').split(',')
    stations = params.get('station') or params.get('sta') or '*'
    stations = stations.replace(' ', '').split(',')
    locations = params.get('location') or params.get('loc') or '*'
    locations = locations.replace(' ', '').split(',')
    channels = params.get('channel') or params.get('cha')
    if not channels:
        msg = 'No channels specified, too much data selected'
        return _error(request, msg, 413)
    channels = channels.replace(' ', '').split(',')
    # output format
    format = params.get('format') or 'mseed'
    if format not in ['mseed']:
        msg = 'Unrecognized output format: %s' % (format)
        return _error(request, msg)
    # nodata
    nodata = params.get('nodata') or '204'
    if nodata not in ['204', '404']:
        msg = 'Invalid value for nodata: %s' % (nodata)
        return _error(request, msg)
    nodata = int(nodata)
    # quality
    quality = params.get('quality') or 'B'
    if quality not in ['D', 'R', 'Q', 'M', 'B', '?', '*']:
        msg = 'Unrecognized quality selection [D,R,Q,M,B,?,*]'
        return _error(request, msg)
    # minimumlength
    minimumlength = params.get('minimumlength') or '0.0'
    try:
        minimumlength = float(minimumlength)
    except ValueError:
        msg = 'Bad numeric value for minimumlength: %s' % (minimumlength)
        return _error(request, msg)
    # longestonly
    longestonly = params.get('longestonly') or ''
    if longestonly not in ['true', 'TRUE', '1', '']:
        msg = 'Bad boolean value for longestonly: %s' % (longestonly)
        return _error(request, msg)
    longestonly = bool(longestonly)
    # process query using celery
    task = process_query.delay(networks, stations, locations, channels,
            starttime.timestamp, endtime.timestamp, format, nodata, quality,
            minimumlength, longestonly)
    # check task status for QUERY_TIMEOUT seconds
    result = AsyncResult(task.task_id)
    try:
        data = result.get(timeout=QUERY_TIMEOUT, interval=0.5)
    except TimeoutError:
        msg = 'Timeout %s' % (task.task_id)
        return _error(request, msg, 413)
    # response
    return HttpResponse(data, content_type="text/plain")
