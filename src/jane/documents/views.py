# -*- coding: utf-8 -*-

from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models, serializer


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
def indexed_values_list(request, resource_type,
                        format=None):  # @ReservedAssignment
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
def indexed_value_detail(request, resource_type, pk,
                         format=None):  # @ReservedAssignment
    """
    Retrieve a single indexed value.
    """
    try:
        value = models.IndexedValue.objects.get(pk=pk)
    except models.IndexedValue.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        data = serializer.IndexedValueSerializer(value).data
        #for d, v in zip(data["attachments"], value.attachments.all()):
        #    d.insert(0, "url", reverse(
        #        view_attachment, args=[resource_type, value.pk, v.pk],
        #        request=request))
        #import pdb;pdb.set_trace()
        return Response(data)


def view_attachment(request, resource_type, index_id, attachment_id):
    # Assure resource type and index id are available.
    value = get_object_or_404(models.IndexedValueAttachment,
        indexed_value__document__resource__resource_type__name=resource_type,
        indexed_value__pk=index_id, pk=attachment_id)

    response = HttpResponse(content_type=value.content_type)
    response.write(value.data)
    return response
