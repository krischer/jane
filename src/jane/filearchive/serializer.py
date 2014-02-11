# -*- coding: utf-8 -*-

from rest_framework import serializers, pagination

from jane.filearchive import models


class WaveformSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Waveform
        fields = ['network', 'station', 'location', 'channel', 'starttime',
            'endtime', 'sampling_rate', 'npts', 'preview_image']


class PaginatedWaveformSerializer(pagination.PaginationSerializer):

    class Meta:
        object_serializer_class = WaveformSerializer
