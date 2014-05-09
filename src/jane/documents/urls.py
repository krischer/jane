# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = patterns('jane.documents.views',
    url(r'^rest/$', 'documents_root'),
    url(r'^rest/(?P<resource_type>\w+)$', 'indexed_values_list'),
    url(r'^rest/(?P<resource_type>\w+)/(?P<pk>[0-9]+)$',
        'indexed_value_detail'),
    url(r'^rest/(?P<resource_type>\w+)/(?P<index_id>[0-9]+)/'
        '(?P<attachment_id>[0-9]+)$',
        'view_attachment'),
    url(r'^(?P<resource_type>[-\w]+)/',
        view='test',
        name='test'),
)

urlpatterns = format_suffix_patterns(urlpatterns)

# XXX: currently fails for initial syncdb
try:
    from .plugins import initialize_plugins
    available_plugins = initialize_plugins()
except:
    pass
