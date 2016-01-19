# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf.urls import include, patterns, url
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = patterns(
    'jane.jane.views',
    url(r'^$', view='index'),
    url(r'^rest/?$', view='rest_root', name='rest_root'),
    url(r'^rest/current_user/$', view='current_user', name='current_user'),
    url(r'^rest/api-auth/', include('rest_framework.urls',
                                    namespace='rest_framework'))
)


urlpatterns = format_suffix_patterns(urlpatterns)
