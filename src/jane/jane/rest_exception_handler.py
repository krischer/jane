# -*- coding: utf-8 -*-
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import exception_handler

from jane import exceptions


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Will not work for custom exceptions.
    if response is None:

        data = {}
        if isinstance(exc, exceptions.JaneException):
            data["reason"] = exc.args[0]
        else:
            return None
        response = Response(data, status=exc.status_code)

    # Now add the HTTP status code to the response.
    if response is not None:
        if isinstance(exc, Http404):
            response.data['status_code'] = "404"
        else:
            response.data['status_code'] = exc.status_code

    return response
