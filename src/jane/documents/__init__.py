# -*- coding: utf-8 -*-

default_app_config = "jane.documents.apps.JaneDocumentsConfig"

# Regular expression used to check for a valid filename. Defined here as its
# used in a number of places and thus its consistent.
DOCUMENT_FILENAME_REGEX = r'[A-Za-z0-9-_.,:]+'
