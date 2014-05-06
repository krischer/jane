# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from rest_framework.reverse import reverse
from rest_framework import generics, renderers

from jane.documents import models, serializer

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


def test(request, resource_type):
    """
    """
    resource_type = get_object_or_404(models.ResourceType, name=resource_type)
    values = models.IndexedValue.objects.\
        filter(document__resource__resource_type=resource_type).\
        extra(where=["json->'longitude' <= '100'",
                     "json->'latitude' <= '50'",
                     "json->'magnitude' > '1'"])

    return render_to_response('documents/test.html',
        {'values': values},
        context_instance=RequestContext(request))


@api_view(['GET'])
def documents_root(request, format=None):
    """
    The root of the jane.documents REST interface. Lists all registered
    resource types.
    """
    if request.method == "GET":
        resource_types = models.ResourceType.objects.all()
        data = {
           _i.name: reverse(indexed_values_list, args=[_i.name],
                            request=request)
           for _i in resource_types
        }
        return Response(data)


@api_view(['GET'])
def indexed_values_list(request, resource_type, format=None):
    """
    Lists all indexed values.
    """
    if request.method == "GET":
        res_type = get_object_or_404(models.ResourceType, name=resource_type)
        values = models.IndexedValue.objects. \
            filter(document__resource__resource_type=res_type)
        data = serializer.IndexedValueSerializer(values, many=True).data
        for d, v in zip(data, values):
            d.insert(0, "url", reverse(indexed_value_detail,
                                       args=[res_type, v.pk],
                                       request=request))
            for _d, _v in zip(d["attachments"], v.attachments.all()):
                _d.insert(0, "url", reverse(
                    view_attachment, args=[res_type, v.pk, _v.pk],
                    request=request))
        return Response(data)


@api_view(['GET'])
def indexed_value_detail(request, resource_type, pk, format=None):
    """
    Retrieve a single indexed value.
    """
    try:
        value = models.IndexedValue.objects.get(pk=pk)
    except models.IndexedValue.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        data = serializer.IndexedValueSerializer(value).data
        for d, v in zip(data["attachments"], value.attachments.all()):
            d.insert(0, "url", reverse(
                view_attachment, args=[resource_type, value.pk, v.pk],
                request=request))
        return Response(data)


def view_attachment(request, resource_type, index_id, attachment_id):
    # Assure resource type and index id are available.
    # XXX: Check relation.
    get_object_or_404(models.ResourceType, name=resource_type)
    get_object_or_404(models.IndexedValue, pk=index_id)
    value = get_object_or_404(models.IndexedValueAttachment, pk=attachment_id)

    response = HttpResponse(mimetype=value.content_type)
    response.write(value.data)
    return response
