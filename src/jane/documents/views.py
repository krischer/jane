# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

import geojson as geojson_module
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
    return HttpResponse(values, content_type='application/json')


@api_view(['GET'])
def record_list(request, resource_type, format=None):  # @ReservedAssignment
    """
    Lists all indexed values.
    """
    if request.method == "GET":
        res_type = get_object_or_404(models.ResourceType, name=resource_type)
        queryset = models.Record.objects. \
            filter(document__resource__resource_type=res_type)

        if request.accepted_renderer.format == 'api':
            # REST API uses pagination
            paginate_by = settings.REST_FRAMEWORK['PAGINATE_BY']
            max_paginate_by = settings.REST_FRAMEWORK['MAX_PAGINATE_BY']
            paginate_by_param = settings.REST_FRAMEWORK['PAGINATE_BY_PARAM']

            # page size
            try:
                # client may set page size
                page_size = int(request.QUERY_PARAMS.get(paginate_by_param))
            except TypeError:
                page_size = paginate_by
            else:
                # but limited by settings
                if page_size > max_paginate_by:
                    page_size = max_paginate_by

            paginator = Paginator(queryset, page_size)

            try:
                records = paginator.page(request.QUERY_PARAMS.get('page'))
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                records = paginator.page(1)
            except EmptyPage:
                # If page is out of range deliver last page of results.
                records = paginator.page(paginator.num_pages)

            data = serializer.PaginatedRecordSerializer(records,
                context={'request': request}).data
        else:
            data = serializer.RecordSerializer(queryset, many=True,
                context={'request': request}).data
        return Response(data)
    else:
        raise Http404


@api_view(['GET'])
def record_detail(request, resource_type, pk,
                       format=None):  # @ReservedAssignment
    """
    Retrieve a single indexed value.
    """
    #resource_type = get_object_or_404(models.ResourceType, name=resource_type)
    value = get_object_or_404(models.Record, pk=pk)

    if request.method == 'GET':
        data = serializer.RecordSerializer(value).data
        for d, v in zip(data["attachments"], value.attachments.all()):
            d["url"] = reverse('attachment_detail',
                               args=[resource_type, value.pk, v.pk],
                               request=request)
        return Response(data)
    else:
        raise Http404


@api_view(['GET'])
def attachment_detail(request, resource_type, index_id, attachment_id):
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
