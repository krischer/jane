# -*- coding: utf-8 -*-


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
    pass


class JaneDocumentAlreadyExists(JaneException):
    """
    Raised when a document already exists in the database.
    """
    pass
