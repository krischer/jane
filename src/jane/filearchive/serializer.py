# -*- coding: utf-8 -*-

from rest_framework import serializers, pagination

from jane.filearchive import models


class WaveformSerializer(serializers.HyperlinkedModelSerializer):
    plot = serializers.HyperlinkedIdentityField(
        view_name='waveform-plot', format='png')

    class Meta:
        model = models.Waveform
        fields = ['url', 'plot', 'network', 'station', 'location', 'channel',
                  'starttime', 'endtime', 'sampling_rate', 'npts']


class PaginatedWaveformSerializer(pagination.PaginationSerializer):

    class Meta:
        object_serializer_class = WaveformSerializer
