# -*- coding: utf-8 -*-
import os

from rest_framework import viewsets, renderers
from rest_framework.response import Response
from rest_framework.decorators import detail_route

from jane.waveforms import models, serializer


class PNGRenderer(renderers.BaseRenderer):
    media_type = "image/png"
    format = "png"

    def render(self, data, media_type=None, renderer_context=None):
        return data


class BinaryRenderer(renderers.BaseRenderer):
    media_type = "application/octet-stream"
    format = "binary"

    def render(self, data, media_type=None, renderer_context=None):
        return data


class WaveformView(viewsets.ReadOnlyModelViewSet):

    def get_queryset(self):
        query = models.ContinuousTrace.objects

        # Limit the queryset depending on the user. If no user is given,
        # all restrictions apply, otherwise only the ones which don't have
        # the user apply.
        user = self.request.user
        if user.is_anonymous():
            restrictions = models.Restriction.objects.all()
        else:
            restrictions = models.Restriction.objects.exclude(users=user)

        for restriction in restrictions:
            query = query.exclude(network=restriction.network,
                                  station=restriction.station)

        return query.all()

    serializer_class = serializer.WaveformSerializer

    @detail_route(renderer_classes=[PNGRenderer])
    def plot(self, request, *args, **kwargs):
        obj = self.get_object()
        return Response(obj.preview_image)

    @detail_route(renderer_classes=[BinaryRenderer])
    def file(self, request, *args, **kwargs):
        file_obj = self.get_object().file
        filename = os.path.join(file_obj.path.name, file_obj.name)
        headers = {
            "Content-Disposition":
                'attachment; filename="%s"' % os.path.basename(filename)
        }
        with open(filename, "rb") as fh:
            return Response(fh.read(), headers=headers)
