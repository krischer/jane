# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from jane.filearchive import views


urlpatterns = patterns('',
    url(r'^rest/waveforms/', views.WaveformListView.as_view(),
        name='rest_waveforms'),
)
