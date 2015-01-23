# -*- coding: utf-8 -*-

import datetime

from django.shortcuts import render_to_response
from django.template.context import RequestContext


def fdnsws_error(request, status_code, service, message, version):
    """
    Standard error page for the FDSN Web Service.
    """
    options = {
        'status_code': status_code,
        'message': message,
        'service': service,
        'version': version,
        'url': request.build_absolute_uri(request.get_full_path()),
        'utcnow': datetime.datetime.utcnow(),
    }
    response = render_to_response("fdsnws/error.txt", options,
                                  RequestContext(request),
                                  content_type="text/plain; charset=utf-8")
    response.status_code = status_code
    response.reason_phrase = message.splitlines()[0]
    return response


def parse_query_parameters(query_params, request):
    """
    Parses query parameters given a request object.

    :param query_params: Parameters definition as dictionary of dictionary.
        The definition of each parameters has to have the following keys:
        ``"aliases"``, ``"type"``, ``"required"``, ``"default"``.
    :type query_params: dict
    :param request: The request object.
    """
    parameters = {}

    for param_name, param_def in query_params.items():
        param = None

        # Try to any of of the possible names.
        for name in param_def["aliases"]:
            param = request.get(name)
            if param is not None:
                break

        if param is None:
            if param_def["required"]:
                return "Parameter '%s' is required." % param_name
            elif param_def["default"] is not None:
                parameters[param_name] = param_def["default"]
            continue

        # Convert types.
        try:
            parameters[param_name] = param_def["type"](param)
        except Exception as e:
            return "Error parsing parameter '%s': %s" % (
                param_name, e)

    return parameters
