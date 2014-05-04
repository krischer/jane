# -*- coding: utf-8 -*-
import os

from rest_framework import viewsets, renderers

from rest_framework.response import Response
from rest_framework.decorators import link

from jane.filearchive import models, serializer


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
    queryset = models.Waveform.objects.all()
    serializer_class = serializer.WaveformSerializer

    @link(renderer_classes=[PNGRenderer])
    def plot(self, request, *args, **kwargs):
        obj = self.get_object()
        return Response(obj.preview_image)

    @link(renderer_classes=[BinaryRenderer])
    def file(self, request, *args, **kwargs):
        file_obj = self.get_object().file
        filename = os.path.join(file_obj.path.name, file_obj.name)
        headers = {
            "Content-Disposition": 'attachment; filename="%s"' % filename
        }
        with open(filename, "rb") as fh:
            return Response(fh.read(), headers=headers)
