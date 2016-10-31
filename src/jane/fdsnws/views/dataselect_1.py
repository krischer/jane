# -*- coding: utf-8 -*-

from uuid import uuid4

from django.conf import settings
from django.http.response import HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from obspy.core.utcdatetime import UTCDateTime

from jane.fdsnws.dataselect_query import query_dataselect
from jane.fdsnws.views.utils import fdnsws_error
from jane.jane.decorators import logged_in_or_basicauth


VERSION = '1.1.1'
QUERY_TIMEOUT = 10


def _error(request, message, status_code=400):
    return fdnsws_error(request, status_code=status_code, service="dataselect",
                        message=message, version=VERSION)


def index(request):
    """
    FDSNWS dataselect Web Service HTML index page.
    """
    context = {
        'host': request.build_absolute_uri('/')[:-1],
        'instance_name': settings.JANE_INSTANCE_NAME,
        'accent_color': settings.JANE_ACCENT_COLOR
    }
    return render(request, "fdsnws/dataselect/1/index.html", context)


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
    return render(request, "fdsnws/dataselect/1/application.wadl", context,
                  content_type="application/xml; charset=utf-8")


def query(request):
    """
    Parses and returns data request
    """
    # handle both: HTTP POST and HTTP GET variables
    params = dict(request.META)
    params.update(dict(getattr(request, request.method)))
    params = {k: (v[0] if isinstance(v, list) else v)
              for k, v in params.items()}

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

    # Three step procedure to be able to raise for empty strings laters on.
    networks = params.get('network')
    if networks is None:
        networks = params.get('net')
    if networks is None:
        networks = "*"
    networks = networks.replace(' ', '').split(',')
    networks = [i.strip().upper() for i in networks]
    # Empty strings are invalid.
    if "" in networks:
        return _error(request=request,
                      message="Network must not be an empty string.",
                      status_code=400)

    stations = params.get('station')
    if stations is None:
        stations = params.get('sta')
    if stations is None:
        stations = "*"
    stations = stations.replace(' ', '').split(',')
    stations = [i.strip().upper() for i in stations]
    # Empty strings are invalid.
    if "" in stations:
        return _error(request=request,
                      message="Station must not be an empty string.",
                      status_code=400)

    locations = params.get('location') or params.get('loc') or '*'
    locations = locations.replace(' ', '').split(',')
    locations = [i.strip().upper() for i in locations]
    # replace empty locations
    locations = [l.replace('--', '') for l in locations]

    channels = params.get('channel')
    if channels is None:
        channels = params.get('cha')
    if channels is None:
        channels = "*"
    channels = channels.replace(' ', '').split(',')
    channels = [i.strip().upper() for i in channels]
    # Empty strings are invalid.
    if "" in channels:
        return _error(request=request,
                      message="Channel must not be an empty string.",
                      status_code=400)

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
    # user
    if request.user.is_authenticated():
        user = request.user
    else:
        user = None

    content = query_dataselect(networks=networks, stations=stations,
                               locations=locations, channels=channels,
                               starttime=starttime, endtime=endtime,
                               format=format, nodata=nodata,
                               minimumlength=minimumlength,
                               longestonly=longestonly, user=user)

    if isinstance(content, int):
        msg = 'Not Found: No data selected'
        return _error(request, msg, content)

    response = StreamingHttpResponse(
        content(),
        content_type='application/octet-stream')
    response['Content-Disposition'] = \
        "attachment; filename=fdsnws_dataselect_1_%s.%s" % (
            str(uuid4())[:6], format.lower())
    return response


@logged_in_or_basicauth(settings.JANE_INSTANCE_NAME)
def queryauth(request):
    """
    Parses and returns data request
    """
    return query(request)
