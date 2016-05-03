# -*- coding: utf-8 -*-

from django.conf.urls import url, include

from jane.fdsnws.views import dataselect_1, station_1, event_1


dataselect_1_urlpatterns = [
    url(r'^$',
        view=dataselect_1.index,
        name='fdsnws_dataselect_1_index'),
    url(r'^version/?$',
        view=dataselect_1.version,
        name='fdsnws_dataselect_1_version'),
    url(r'^application.wadl/?$',
        view=dataselect_1.wadl,
        name='fdsnws_dataselect_1_wadl'),
    url(r'^query/?$',
        view=dataselect_1.query,
        name='fdsnws_dataselect_1_query'),
    url(r'^queryauth/?$',
        view=dataselect_1.queryauth,
        name='fdsnws_dataselect_1_queryauth')
]

station_1_urlpatterns = [
    url(r'^$',
        view=station_1.index,
        name='fdsnws_station_1_index'),
    url(r'^version/?$',
        view=station_1.version,
        name='fdsnws_station_1_version'),
    url(r'^application.wadl/?$',
        view=station_1.wadl,
        name='fdsnws_station_1_wadl'),
    url(r'^query/?$',
        view=station_1.query,
        name='fdsnws_station_1_query'),
    url(r'^queryauth/?$',
        view=station_1.queryauth,
        name='fdsnws_station_1_queryauth')
]

event_1_urlpatterns = [
    url(r'^$',
        view=event_1.index,
        name='fdsnws_event_1_index'),
    url(r'^version/?$',
        view=event_1.version,
        name='fdsnws_event_1_version'),
    url(r'^contributors/?$',
        view=event_1.contributors,
        name='fdsnws_event_1_contributors'),
    url(r'^catalogs/?$',
        view=event_1.catalogs,
        name='fdsnws_event_1_catalogs'),
    url(r'^application.wadl/?$',
        view=event_1.wadl,
        name='fdsnws_event_1_wadl'),
    url(r'^query/?$',
        view=event_1.query,
        name='fdsnws_event_1_query'),
    url(r'^queryauth/?$',
        view=event_1.queryauth,
        name='fdsnws_event_1_queryauth')
]


urlpatterns = [
    url(r'^dataselect/1/', include(dataselect_1_urlpatterns)),
    url(r'^station/1/', include(station_1_urlpatterns)),
    url(r'^event/1/', include(event_1_urlpatterns)),
]
