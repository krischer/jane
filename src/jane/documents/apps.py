# -*- coding: utf-8 -*-
from django.apps import AppConfig


class JaneDocumentsConfig(AppConfig):
    name = 'jane.documents'
    verbose_name = "Jane's Document Database"

    def ready(self):
        # Import signals to activate their @receiver decorator. Don't do
        # this in the __init__.py to avoid loading models during the app
        # setup stage which Django does not like that much.
        from . import signals  # NOQA
