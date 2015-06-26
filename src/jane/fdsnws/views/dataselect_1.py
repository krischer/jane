# -*- coding: utf-8 -*-

import base64
import io
import os
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.servers.basehttp import FileWrapper
from django.http.response import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from obspy.core.utcdatetime import UTCDateTime

from jane.fdsnws.dataselect_query import query_dataselect
from jane.fdsnws.views.utils import fdnsws_error


VERSION = '1.1.1'
QUERY_TIMEOUT = 10


def _error(request, message, status_code=400):
    return fdnsws_error(request, status_code=status_code, service="dataselect",
                        message=message, version=VERSION)


def index(request):
    """
    FDSNWS dataselect Web Service HTML index page.
    """
    options = {
        'host': request.build_absolute_uri('/')[:-1],
        'instance_name': settings.JANE_INSTANCE_NAME,
        'accent_color': settings.JANE_ACCENT_COLOR
    }
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
    return render_to_response(
        "fdsnws/dataselect/1/application.wadl", options,
        RequestContext(request), content_type="application/xml; charset=utf-8")


def query(request, user=None):
    """
    Parses and returns data request
    """
    # handle both: HTTP POST and HTTP GET variables
    params = getattr(request, request.method)

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
    networks = [i.strip().upper() for i in networks]
    stations = params.get('station') or params.get('sta') or '*'
    stations = stations.replace(' ', '').split(',')
    stations = [i.strip().upper() for i in stations]
    locations = params.get('location') or params.get('loc') or '*'
    locations = locations.replace(' ', '').split(',')
    locations = [i.strip().upper() for i in locations]
    # replace empty locations
    locations = [l.replace('--', '') for l in locations]
    channels = params.get('channel') or params.get('cha')
    if not channels:
        msg = 'No channels specified, too much data selected'
        return _error(request, msg, 413)
    channels = channels.replace(' ', '').split(',')
    channels = [i.strip().upper() for i in channels]
    # output format
    format = params.get('format') or 'mseed'
    if format not in ['mseed', 'gse2', 'sac']:
        msg = 'Unrecognized output format: %s' % (format)
        return _error(request, msg)
    # nodata
    nodata = params.get('nodata') or 204
    try:
        nodata = int(nodata)
    except ValueError:
        msg = 'Bad numeric value for nodata: %s' % (nodata)
        return _error(request, msg)
    if nodata not in [204, 404]:
        msg = 'Invalid value for nodata: %s' % (nodata)
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
    username = user.username if user else None

    with io.BytesIO() as fh:
        status = query_dataselect(fh=fh, networks=networks, stations=stations,
                                  locations=locations, channels=channels,
                                  starttime=starttime, endtime=endtime,
                                  format=format, nodata=nodata,
                                  minimumlength=minimumlength,
                                  longestonly=longestonly, username=username)
        fh.seek(0, 0)
        mem_file = FileWrapper(fh)

        if status == 200:
            response = HttpResponse(mem_file,
                                    content_type='application/octet-stream')
            response['Content-Disposition'] = \
                "attachment; filename=fdsnws_dataselect_1_%s.%s" % (
                    str(uuid4())[:6], format.lower())
            return response
        else:
            msg = 'Not Found: No data selected'
            return _error(request, msg, status)


def queryauth(request):
    """
    Parses and returns data request
    """
    if request.META.get('HTTP_AUTHORIZATION', False):
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2 and auth[0].lower() == 'basic':
            # basic auth
            auth = base64.b64decode(auth[1])
            username, password = auth.decode("utf-8").split(':')
            # authenticate
            user = authenticate(username=username, password=password)
            if user is not None:
                return query(request, user)
    # otherwise
    response = HttpResponse("Auth Required", status=401)
    response['WWW-Authenticate'] = 'Basic realm="restricted area"'
    return response
