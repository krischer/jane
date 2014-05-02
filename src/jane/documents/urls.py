# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url


urlpatterns = patterns('jane.documents.views',
    url(r'^(?P<resource_type>[-\w]+)/',
        view='test',
        name='test'),
)
