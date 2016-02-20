# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf.urls import patterns, url, include


dataselect_1_urlpatterns = patterns(
    'jane.fdsnws.views.dataselect_1',
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
        name='fdsnws_dataselect_1_queryauth')
)


station_1_urlpatterns = patterns(
    'jane.fdsnws.views.station_1',
    url(r'^$',
        view='index',
        name='fdsnws_station_1_index'),
    url(r'^version/?$',
        view='version',
        name='fdsnws_station_1_version'),
    url(r'^application.wadl/?$',
        view='wadl',
        name='fdsnws_station_1_wadl'),
    url(r'^query/?$',
        view='query',
        name='fdsnws_station_1_query'),
    url(r'^queryauth/?$',
        view='queryauth',
        name='fdsnws_station_1_queryauth')
    )


event_1_urlpatterns = patterns(
    'jane.fdsnws.views.event_1',
    url(r'^$',
        view='index',
        name='fdsnws_event_1_index'),
    url(r'^version/?$',
        view='version',
        name='fdsnws_event_1_version'),
    url(r'^contributors/?$',
        view='contributors',
        name='fdsnws_event_1_contributors'),
    url(r'^catalogs/?$',
        view='catalogs',
        name='fdsnws_event_1_catalogs'),
    url(r'^application.wadl/?$',
        view='wadl',
        name='fdsnws_event_1_wadl'),
    url(r'^query/?$',
        view='query',
        name='fdsnws_event_1_query'),
    url(r'^queryauth/?$',
        view='queryauth',
        name='fdsnws_event_1_queryauth')
    )


urlpatterns = patterns(
    '',
    url(r'^dataselect/1/', include(dataselect_1_urlpatterns)),
    url(r'^station/1/', include(station_1_urlpatterns)),
    url(r'^event/1/', include(event_1_urlpatterns)),
)
