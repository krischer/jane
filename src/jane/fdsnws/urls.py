# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf.urls import patterns, url, include


dataselect_1_urlpatterns = patterns('jane.fdsnws.views.dataselect_1',
    url(r'^$',
        view='index',
        name='fdsnws_dataselect_1_index'),
    url(r'^version/?$',
        view='version',
        name='fdsnws_dataselect_1_version'),
    url(r'^application.wadl/?$',
        view='wadl',
        name='fdsnws_dataselect_1_wadl'),
    url(r'^query/?$',
        view='query',
        name='fdsnws_dataselect_1_query'),
    url(r'^queryauth/?$',
        view='queryauth',
        name='fdsnws_dataselect_1_queryauth'),
    url(r'^result/(?P<task_id>[-\w]+)/$',
        view='result',
        name='fdsnws_dataselect_1_result'),
)


urlpatterns = patterns('',
    url(r'^dataselect/1/', include(dataselect_1_urlpatterns)),
#    url(r'^event/1/', include('jane.fdsnws.event.urls')),
#    url(r'^station/1/', include('jane.fdsnws.station.urls')),
)
