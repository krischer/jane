# -*- coding: utf-8 -*-

import datetime

from django.shortcuts import render_to_response
from django.template.context import RequestContext


def fdnsws_error(request, status_code, message, version):
    """
    Standard error page for the FDSN Web Service.
    """
    options = {
        'status_code': status_code,
        'message': message,
        'version': version,
        'url': request.build_absolute_uri(request.get_full_path()),
        'utcnow': datetime.datetime.utcnow(),
    }
    response = render_to_response("fdsnws/error.txt", options,
        RequestContext(request), content_type="text/plain; charset=utf-8")
    response.status_code = status_code
    response.reason_phrase = message
    return response
