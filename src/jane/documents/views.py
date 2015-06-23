# -*- coding: utf-8 -*-

import collections
import hashlib
import io

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models, serializer, DOCUMENT_FILENAME_REGEX

from rest_framework import viewsets, generics, mixins


CACHE_TIMEOUT = 60 * 60 * 24


class DocumentsView(mixins.RetrieveModelMixin, mixins.ListModelMixin,
                    viewsets.ViewSetMixin, generics.GenericAPIView):
    serializer_class = serializer.DocumentSerializer

    lookup_field = 'name'
    lookup_value_regex = DOCUMENT_FILENAME_REGEX

    def get_queryset(self):
        doctype = get_object_or_404(models.DocumentType,
                                    name=self.kwargs['document_type'])
        queryset = models.Document.objects.filter(document_type=doctype)

        doctype = models.DocumentType.objects.get(
            name=self.kwargs["document_type"])
        retrieve_permissions = doctype.retrieve_permissions.all()
        if retrieve_permissions:
            for perm in retrieve_permissions:
                perm = perm.get_plugin()
                if self.request.user.has_perm(
                        "documents." + perm.permission_codename):
                    queryset = perm.filter_queryset_user_has_permission(
                        queryset, model_type="document")
                else:
                    queryset = \
                        perm.filter_queryset_user_does_not_have_permission(
                            queryset, model_type="document")
        return queryset

    def update(self, request, document_type, name):
        """
        Method called upon "PUT"ting a new document. Creates a new or
        replaces an existing document.
        """
        status = models.Document.objects.add_or_modify_document(
            document_type=document_type,
            name=name,
            data=request.data.body,
            user=request.user)

        return Response(
            {"status": "Successfully created or updated the document"},
            status=status)


class DocumentIndicesView(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializer.DocumentIndexSerializer

    def get_queryset(self):
        # Get the query dictionary.
        query = dict(self.request.QUERY_PARAMS)
        # Remove some that might be due to the API.
        if "offset" in query:
            del query["offset"]
        if "format" in query:
            del query["format"]
        # Flatten the rest.
        query = {key: value[0] for key, value in query.items()}

        queryset = models.DocumentIndex.objects.get_filtered_queryset(
            document_type=self.kwargs["document_type"], **query)

        # Apply potential additional restrictions based on the permissions.
        doctype = models.DocumentType.objects.get(
            name=self.kwargs["document_type"])
        retrieve_permissions = doctype.retrieve_permissions.all()
        if retrieve_permissions:
            for perm in retrieve_permissions:
                perm = perm.get_plugin()
                # XXX: Any way to dynamically fill the 'documents.' part?
                if self.request.user.has_perm(
                        "documents." + perm.permission_codename):
                    queryset = perm.filter_queryset_user_has_permission(
                        queryset, model_type="index")
                else:
                    queryset = \
                        perm.filter_queryset_user_does_not_have_permission(
                            queryset=queryset, model_type="index")
        return queryset


class DocumentIndexAttachmentsView(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializer.DocumentIndexAttachmentSerializer

    def get_queryset(self):
        index = get_object_or_404(models.DocumentIndex,
                                  pk=self.kwargs['idx'])
        return models.DocumentIndexAttachment.objects.filter(index=index)


@api_view(['GET'])
def documents_rest_root(request, format=None):
    """
    Index of all document types.
    """
    if request.method == "GET":
        document_types = [_i.name for _i in models.DocumentType.objects.all()]

        data = [(_i, reverse("rest_documents-list",
                             kwargs={"document_type": _i}, request=request))
                for _i in document_types]

        # Use OrderedDict to force order in browseable REST API.
        return Response([
            collections.OrderedDict([
                ('document_type', i[0]),
                ('url', i[1]),
                ('description', models.DocumentType.objects.get(name=i[0])
                 .definition.get_plugin().title),
                ('available_documents',
                 models.Document.objects.filter(document_type=i[0]).count())]
            ) for i in sorted(data, key=lambda x: x[0])
        ])
    else:
        raise Http404


@api_view(['GET'])
def documents_indices_rest_root(request, format=None):
    """
    Index of all document types for the document indices.
    """
    if request.method == "GET":
        document_types = [_i.name for _i in models.DocumentType.objects.all()]

        data = [(_i, reverse("rest_document_indices-list",
                             kwargs={"document_type": _i}, request=request))
                for _i in document_types]

        # Use OrderedDict to force order in browseable REST API.
        return Response([
            collections.OrderedDict([
                ('document_type', i[0]),
                ('url', i[1]),
                ('description', models.DocumentType.objects.get(name=i[0])
                 .definition.get_plugin().title),
                ('available_documents',
                 models.DocumentIndex.objects.filter(
                     document__document_type=i[0]).count())]
            ) for i in sorted(data, key=lambda x: x[0])
        ])
    else:
        raise Http404


@api_view(['GET', 'POST'])
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
    # Posting will add a new model.
    elif request.method == "POST":
        # Optional filename and name parameters.
        filename = request.stream.META["HTTP_FILENAME"] \
            if "HTTP_FILENAME" in request.stream.META else None
        name = request.stream.META["HTTP_NAME"] \
            if "HTTP_NAME" in request.stream.META else None

        res_type = get_object_or_404(models.DocumentType, name=document_type)

        with io.BytesIO(request.stream.read()) as buf:
            sha1 = hashlib.sha1(buf.read()).hexdigest()

            qs = models.Document.objects.filter(sha1=sha1).exists()
            if qs is True:
                msg = "File already exists in the database."
                return Response(msg, status=status.HTTP_409_CONFLICT)

            buf.seek(0, 2)
            size = buf.tell()
            buf.seek(0, 0)

            document = models.Document(
                document_type=res_type,
                filename=filename,
                name=name,
                data=buf.read(),
                filesize=size,
                sha1=sha1
            )
            document.save()

        return Response("", status=status.HTTP_201_CREATED)
    else:
        raise Http404


@api_view(['GET', 'POST', 'DELETE', 'PUT'])
def record_detail(request, document_type, pk,
                  format=None):  # @ReservedAssignment
    """
    Retrieve a single indexed value.

    POSTing to this url will create a new attachment.
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
    # POSTing adds a new attachment.
    elif request.method == 'POST':
        content_type = request.content_type
        category = request.stream.META["HTTP_CATEGORY"]

        models.DocumentIndexAttachment(
            index=value, category=category,
            content_type=content_type,
            data=request.stream.read()).save()
        return Response("", status=status.HTTP_201_CREATED)
    # DELETEing deletes the corresponding Document. NOT REST compliant but
    # fairly convenient.
    elif request.method == 'DELETE':
        value.document.delete()
        return Response("", status=status.HTTP_200_OK)
    # PUTing changed a document and all associated indices. Again not REST
    # compliant but fairly convenient to use.
    elif request.method == 'PUT':
        # Optional filename and name parameters.
        filename = request.stream.META["HTTP_FILENAME"] \
            if "HTTP_FILENAME" in request.stream.META else None
        name = request.stream.META["HTTP_NAME"] \
            if "HTTP_NAME" in request.stream.META else None

        with io.BytesIO(request.stream.read()) as buf:
            sha1 = hashlib.sha1(buf.read()).hexdigest()

            qs = models.Document.objects.filter(sha1=sha1).exists()
            if qs is True:
                msg = "File already exists in the database."
                return Response(msg, status=status.HTTP_409_CONFLICT)

            buf.seek(0, 2)
            size = buf.tell()
            buf.seek(0, 0)

            document = value.document

            document.filename = filename
            document.name = name
            document.data = buf.read()
            document.filesize = size
            document.sha1 = sha1
            document.save()

        return Response("", status=status.HTTP_201_CREATED)
    else:
        raise Http404


@api_view(['GET', 'DELETE', 'PUT'])
def attachment_detail(request, document_type, index_id, attachment_id):
    """
    Getting an attachment will return the actual attachment with the proper
    content-type.

    Attachments can also be deleted.
    """
    # Assure document type and index id are available.
    value = get_object_or_404(
        models.DocumentIndexAttachment,
        index__pk=index_id, pk=attachment_id,
        index__document__document_type__name=document_type)

    if request.method == 'GET':
        response = HttpResponse(content_type=value.content_type)
        response.write(value.data)
        return response
    elif request.method == 'DELETE':
        value.delete()
        return Response("", status=status.HTTP_200_OK)
    elif request.method == "PUT":
        content_type = request.content_type
        category = request.stream.META["HTTP_CATEGORY"]

        value.category = category
        value.content_type = content_type
        value.data = request.stream.read()
        value.save()

        return Response("", status=status.HTTP_200_OK)
    else:
        raise Http404


def document_data(request, document_type, name, *args, **kwargs):
    """
    Get the data for the document corresponding to a certain document type
    and name.
    """
    document = get_object_or_404(models.Document,
                                 document_type__name=document_type, name=name)
    return HttpResponse(content=document.data,
                        content_type=document.content_type)


def attachment_data(request, pk, *args, **kwargs):
    """
    Get the data for the attachment with a certain id.
    """
    attachment = get_object_or_404(models.DocumentIndexAttachment, pk=pk)
    return HttpResponse(content=attachment.data,
                        content_type=attachment.content_type)
