# -*- coding: utf-8 -*-
from django.conf.urls import url, include

from jane.jane.utils import OptionalTrailingSlashSimpleRouter
from jane.waveforms import views


router = OptionalTrailingSlashSimpleRouter(trailing_slash=False)
router.register(r'waveforms', views.WaveformView, base_name='rest_waveforms')

urlpatterns = [
    url(r'^rest/', include(router.urls)),
]
