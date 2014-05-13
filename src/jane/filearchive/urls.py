# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url, include
from rest_framework.routers import SimpleRouter

from jane.filearchive import views


router = SimpleRouter(trailing_slash=False)
router.register(r'waveforms', views.WaveformView)

urlpatterns = patterns('',
    url(r'^rest/', include(router.urls)),
)
