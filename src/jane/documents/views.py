# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models, serializer


CACHE_TIMEOUT = 60 * 60 * 24


@api_view(['GET'])
def record_list(request, document_type, format=None):  # @ReservedAssignment
    """
    Lists all indexed values.
    """
    if request.method == "GET":

        res_type = get_object_or_404(models.DocumentType, name=document_type)

        # check for cached version
        if request.accepted_renderer.format == 'json':
            record_list_json = cache.get('record_list_json' + document_type)
            if record_list_json:
                return Response(record_list_json)

        queryset = models.DocumentRevisionIndex.objects. \
            filter(revision__document__document_type=res_type)

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

            data = serializer.PaginatedRecordSerializer(records,
                context=context).data
        else:
            data = serializer.RecordSerializer(queryset, many=True,
                context=context).data
            # cache json requests
            if request.accepted_renderer.format == 'json':
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
    #document_type = get_object_or_404(models.DocumentType, name=document_type)
    value = get_object_or_404(models.DocumentRevisionIndex, pk=pk)

    if request.method == 'GET':
        data = serializer.RecordSerializer(value).data
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
    value = get_object_or_404(models.DocumentRevisionIndexAttachment,
                               record__pk=index_id, pk=attachment_id, **{
        "document_revision_index__document_revision_document__document_"
        "type__name": document_type,

                                                                         }
       )

    if request.method == 'GET':
        response = HttpResponse(content_type=value.content_type)
        response.write(value.data)
        return response
    else:
        raise Http404


def document_revision(request, pk):
    revision = get_object_or_404(models.DocumentRevision, pk=pk)
    if request.method == 'GET':
        response = HttpResponse(content_type=revision.content_type)
        response.write(revision.data)
        return response
    else:
        raise Http404
