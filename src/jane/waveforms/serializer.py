# -*- coding: utf-8 -*-

from rest_framework import serializers, pagination

from jane.waveforms import models


class WaveformSerializer(serializers.HyperlinkedModelSerializer):
    plot = serializers.HyperlinkedIdentityField(
        view_name='waveform-plot', format='png')
    containing_file = serializers.HyperlinkedIdentityField(
        view_name='waveform-file', format='binary')

    class Meta:
        model = models.ContinuousTrace
        fields = ['url', 'plot', 'containing_file', 'network', 'station',
                  'location', 'channel', 'starttime', 'endtime',
                  'sampling_rate', 'npts']


class PaginatedWaveformSerializer(pagination.PaginationSerializer):
    """
    Serializes page objects of waveform querysets.
    """
    pages = serializers.Field(source='paginator.num_pages')

    class Meta:
        object_serializer_class = WaveformSerializer
