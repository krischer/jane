# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from jane.fdsnws.views.utils import fdnsws_error


VERSION = '1.1.1'
QUERY_TIMEOUT = 10


def _error(request, message, status_code=400):
    return fdnsws_error(request, status_code=status_code, service="event",
                        message=message, version=VERSION)


def index(request):
    """
    FDSNWS event Web Service HTML index page.
    """
    options = {
        'host': request.build_absolute_uri('/')[:-1],
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
        RequestContext(request), content_type="application/xml; charset=utf-8")


def query(request, debug=False):
    """
    Parses and returns data request
    """
    raise NotImplementedError


@login_required
def queryauth(request, debug=False):
    """
    Parses and returns data request
    """
    return query(request, debug=debug)


def result(request, task_id):  # @UnusedVariable
    """
    Returns requested waveform file
    """
    raise NotImplementedError
