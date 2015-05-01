# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = patterns(
    'jane.documents.views',
    url(r'^rest/(?P<document_type>\w+)/$',
        view='record_list',
        name='record_list'),
    url(r'^rest/(?P<document_type>\w+)/(?P<pk>[0-9]+)/$',
        view='record_detail',
        name='record_detail'),
    url(r'^rest/(?P<document_type>\w+)/(?P<index_id>[0-9]+)/'
        '(?P<attachment_id>[0-9]+)/$',
        view='attachment_detail',
        name='attachment_detail')
)

urlpatterns = format_suffix_patterns(urlpatterns)

# XXX: currently fails for initial syncdb
try:
    from .plugins import initialize_plugins
    available_plugins = initialize_plugins()
except:
    pass
