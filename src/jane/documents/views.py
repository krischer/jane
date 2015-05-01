# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models, serializer, utils


CACHE_TIMEOUT = 60 * 60 * 24


@api_view(['GET'])
def record_list(request, document_type, format=None):  # @ReservedAssignment
    """
    Lists all indexed values.
    """
    if request.method == "GET":
        # check for cached version
        if request.accepted_renderer.format == 'json' and \
                not request.QUERY_PARAMS:
            record_list_json = cache.get('record_list_json' + document_type)
            if record_list_json:
                return Response(record_list_json)

        # Perform potentially complex queries on the JSON indices.
        queryset = utils.get_document_index_queryset(
            document_type=document_type,
            query_params=request.QUERY_PARAMS)

        context = {'request': request, 'resource_type_name': document_type}

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

            data = serializer.PaginatedRecordSerializer(
                records, context=context).data
        else:
            data = serializer.RecordSerializer(queryset, many=True,
                                               context=context).data
            # cache json requests
            if request.accepted_renderer.format == 'json' and \
                    not request.QUERY_PARAMS:
                cache.set('record_list_json' + document_type, data,
                          CACHE_TIMEOUT)
        return Response(data)
    else:
        raise Http404


@api_view(['GET'])
def record_detail(request, document_type, pk,
                  format=None):  # @ReservedAssignment
    """
    Retrieve a single indexed value.
    """
    # document_type = get_object_or_404(models.DocumentType,
    # name=document_type)
    value = get_object_or_404(models.DocumentIndex, pk=pk)

    if request.method == 'GET':
        context = {'request': request, 'resource_type_name': document_type}
        data = serializer.RecordSerializer(value, context=context).data
        for d, v in zip(data["attachments"], value.attachments.all()):
            d["url"] = reverse('attachment_detail',
                               args=[document_type, value.pk, v.pk],
                               request=request)
        return Response(data)
    else:
        raise Http404


@api_view(['GET'])
def attachment_detail(request, document_type, index_id, attachment_id):
    # Assure document type and index id are available.
    value = get_object_or_404(
        models.DocumentIndexAttachment,
        index__pk=index_id, pk=attachment_id,
        index__document__document_type__name=document_type)

    if request.method == 'GET':
        response = HttpResponse(content_type=value.content_type)
        response.write(value.data)
        return response
    else:
        raise Http404


def document_data(request, pk, *args, **kwargs):
    """
    Get the data for the document corresponding to the index id.
    """
    document = models.DocumentIndex.objects.filter(pk=pk).first().document
    return HttpResponse(document.data, document.content_type)
