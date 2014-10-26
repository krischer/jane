# -*- coding: utf-8 -*-

from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
import geojson as geojson_module
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models, serializer


def test(request, resource_type):
    """
    """
    resource_type = get_object_or_404(models.ResourceType, name=resource_type)
    values = models.Record.objects.\
        filter(document__resource__resource_type=resource_type).\
        extra(where=["json->'longitude' <= '100'",
                     "json->'latitude' <= '50'",
                     "json->'magnitude' > '1'"])

    return render_to_response('documents/test.html',
        {'values': values},
        context_instance=RequestContext(request))


def geojson(request, resource_type):
    """
    """
    resource_type = get_object_or_404(models.ResourceType, name=resource_type)
    values = models.Record.objects.\
        filter(document__resource__resource_type=resource_type)
    values = geojson_module.dumps(
        geojson_module.GeometryCollection([
            _i.__geo_interface__ for _i in values])
    )
    return HttpResponse(values, mimetype='application/json')


@api_view(['GET'])
def rest_records_list(request, resource_type,
                      format=None):  # @ReservedAssignment
    """
    Lists all indexed values.
    """
    if request.method == "GET":
        res_type = get_object_or_404(models.ResourceType, name=resource_type)
        values = models.Record.objects. \
            filter(document__resource__resource_type=res_type)
        data = serializer.RecordSerializer(values, many=True).data
        for d, v in zip(data, values):
            d["url"] = reverse('rest_record_detail', args=[res_type, v.pk],
                               request=request)
            for _d, _v in zip(d["attachments"], v.attachments.all()):
                _d["url"] = reverse('rest_attachment_view',
                                    args=[res_type, v.pk, _v.pk],
                                    request=request)
        return Response(data)
    else:
        raise Http404


@api_view(['GET'])
def rest_record_detail(request, resource_type, pk,
                       format=None):  # @ReservedAssignment
    """
    Retrieve a single indexed value.
    """
    value = get_object_or_404(models.Record, pk=pk)

    if request.method == 'GET':
        data = serializer.RecordSerializer(value).data
        for d, v in zip(data["attachments"], value.attachments.all()):
            d["url"] = reverse('rest_attachment_view',
                               args=[resource_type, value.pk, v.pk],
                               request=request)
        return Response(data)
    else:
        raise Http404


@api_view(['GET'])
def rest_attachment_view(request, resource_type, index_id, attachment_id):
    # Assure resource type and index id are available.
    value = get_object_or_404(models.Attachment,
        record__document__resource__resource_type__name=resource_type,
        record__pk=index_id, pk=attachment_id)

    if request.method == 'GET':
        response = HttpResponse(content_type=value.content_type)
        response.write(value.data)
        return response
    else:
        raise Http404
