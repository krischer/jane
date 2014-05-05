# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import patterns, url


urlpatterns = patterns('jane.documents.views',
    url(r'^(?P<resource_type>[-\w]+)/',
        view='test',
        name='test'),
)


from .plugins import initialize_plugins
available_plugins = initialize_plugins()
