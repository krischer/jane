# -*- coding: utf-8 -*-
from rest_framework import status


class JaneException(Exception):
    """
    Base Jane exception.
    """
    pass


class JaneNotAuthorizedException(JaneException):
    """
    Exception raised when the current user is not authorized to perform a
    certain action.
    """
    status_code = status.HTTP_401_UNAUTHORIZED


class JaneDocumentAlreadyExists(JaneException):
    """
    Raised when a document already exists in the database.
    """
    status_code = status.HTTP_409_CONFLICT
