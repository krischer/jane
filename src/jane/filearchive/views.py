# -*- coding: utf-8 -*-

from rest_framework import generics

from jane.filearchive import models, serializer


class WaveformListView(generics.ListAPIView):
    queryset = models.Waveform.objects.all()
    serializer_class = serializer.WaveformSerializer
    filter_fields = ['network', 'station', 'location', 'channel',
        'sampling_rate']
