# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url, include

from rest_framework.routers import DefaultRouter

from jane.filearchive import views


router = DefaultRouter()
router.register(r'waveforms', views.WaveformView)

urlpatterns = patterns('',
    url(r'^rest/', include(router.urls)),
)
