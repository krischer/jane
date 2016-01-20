# -*- coding: utf-8 -*-
from rest_framework import serializers

from jane.waveforms import models


class WaveformSerializer(serializers.HyperlinkedModelSerializer):
    containing_file = serializers.HyperlinkedIdentityField(
        view_name='rest_waveforms-file', format='binary')
    url = serializers.HyperlinkedIdentityField(
        view_name='rest_waveforms-detail',
        lookup_field='pk'
    )

    starttime = serializers.DateTimeField(
        source="timerange.lower",
        format="%Y-%m-%dT%H:%M:%S.%fZ")
    endtime = serializers.DateTimeField(
        source="timerange.upper",
        format="%Y-%m-%dT%H:%M:%S.%fZ")

    class Meta:
        model = models.ContinuousTrace
        fields = ['url', 'containing_file', 'network', 'station', 'location',
                  'channel', 'starttime', 'endtime', 'duration',
                  'sampling_rate', 'quality', 'npts', 'created_at']
