# -*- coding: utf-8 -*-
import collections

from django.db.models.aggregates import Count
from django.http import HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework import viewsets, generics, mixins
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models, serializer, DOCUMENT_FILENAME_REGEX
from jane.exceptions import JaneInvalidRequestException


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
            {"status": "Successfully created or updated the document",
             "status_code": status},
            status=status)

    def destroy(self, request, document_type, name):
        """
        Called upon "DELETING" a resource.
        """
        models.Document.objects.delete_document(
            document_type=document_type, name=name, user=request.user)

        return Response(
            {"status": "Successfully deleted the document",
             "status_code": status.HTTP_204_NO_CONTENT},
            status=status.HTTP_204_NO_CONTENT)


class DocumentIndicesView(viewsets.ReadOnlyModelViewSet):
    serializer_class = serializer.DocumentIndexSerializer

    def get_queryset(self):
        # Get the query dictionary.
        params = dict(self.request.query_params)
        # Remove some that might be due to the API.
        if "offset" in params:
            del params["offset"]
        if "format" in params:
            del params["format"]
        # Flatten the rest.
        params = {key: value[0] for key, value in params.items()}

        queryset = models.DocumentIndex.objects.get_filtered_queryset(
            document_type=self.kwargs["document_type"], **params)

        # annotate number of attachments
        queryset = queryset.\
            annotate(attachments_count=Count('attachments'))

        # Apply potential additional restrictions based on the permissions.
        doctype = models.DocumentType.objects.get(
            name=self.kwargs["document_type"])
        retrieve_permissions = doctype.retrieve_permissions.all()
        if retrieve_permissions:
            for perm in retrieve_permissions:
                perm = perm.get_plugin()
                app_label = models.DocumentType._meta.app_label
                perm_name = "%s.%s" % (app_label,  perm.permission_codename)
                if self.request.user.has_perm(perm_name):
                    queryset = perm.filter_queryset_user_has_permission(
                        queryset, model_type="index")
                else:
                    queryset = \
                        perm.filter_queryset_user_does_not_have_permission(
                            queryset=queryset, model_type="index")
        return queryset


class DocumentIndexAttachmentsView(mixins.RetrieveModelMixin,
                                   mixins.ListModelMixin,
                                   viewsets.ViewSetMixin,
                                   generics.GenericAPIView):
    serializer_class = serializer.DocumentIndexAttachmentSerializer

    def get_queryset(self):
        index = get_object_or_404(models.DocumentIndex,
                                  pk=self.kwargs['idx'])
        return models.DocumentIndexAttachment.objects.filter(index=index)

    def destroy(self, request, document_type, idx, pk):
        """
        Called upon "DELETING" a resource.

        :param document_type: The document type.
        :param idx: The document index id.
        :param pk: The primary key of the attachment.
        """
        models.DocumentIndexAttachment.objects.delete_attachment(
            document_type=document_type, pk=pk, user=request.user)

        return Response(
            {"status": "Successfully deleted the document",
             "status_code": status.HTTP_204_NO_CONTENT},
            status=status.HTTP_204_NO_CONTENT)

    def create(self, request, document_type, idx, pk=None):
        """
        Called when "POSTING" a new attachment.
        """
        # Two headers must be given. The content type is usually always set.
        if "HTTP_CATEGORY" not in request.stream.META:
            raise JaneInvalidRequestException("The 'category' must be passed "
                                              "in the HTTP header.")
        category = request.stream.META["HTTP_CATEGORY"]

        models.DocumentIndexAttachment.objects.add_or_modify_attachment(
            document_type=document_type,
            index_id=idx,
            content_type=request.content_type,
            category=category,
            data=request.data.body,
            user=request.user,
            pk=pk)

        return Response(
            {"status": "Successfully added an attachment.",
             "status_code": status.HTTP_201_CREATED},
            status=status.HTTP_201_CREATED)

    def update(self, request, document_type, idx, pk):
        """
        Method called upon "PUT"ting an attachment. Modifies an existing
        document.
        """
        return self.create(request=request, document_type=document_type,
                           idx=idx, pk=pk)


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
