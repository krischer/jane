# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns


urlpatterns = patterns('jane.core.views',
    url(r'^rest/$', view='rest_root', name='rest_root'),
)

urlpatterns = format_suffix_patterns(urlpatterns)
