# -*- coding: utf-8 -*-

from rest_framework import serializers

from jane.documents import models


class DocumentTypeHyperlinkedIdentifyField(
        serializers.HyperlinkedIdentityField):
    """
    The document and document indices views are parametrized with the
    document type. The default HyperlinkedIdentifyField class cannot deal
    with this. This version can.

    Also has support for nested lookup fields.
    """
    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if obj.pk is None:
            return None

        # Enables to lookup for example `document__name`
        lookups = self.lookup_field.split("__")
        lookup_value = getattr(obj, lookups.pop(0))
        while lookups:
            lookup_value = getattr(lookup_value, lookups.pop(0))
        kwargs = {self.lookup_url_kwarg: lookup_value}

        # Deal with documents as well as indices and attachments.
        if hasattr(obj, "document_type"):
            kwargs["document_type"] = obj.document_type.name
        elif hasattr(obj, "document"):
            kwargs["document_type"] = obj.document.document_type.name
        else:
            kwargs["document_type"] = obj.index.document.document_type.name
            kwargs["idx"] = obj.index_id

        url = self.reverse(view_name, kwargs=kwargs, request=request,
                           format=format)
        return url


class DocumentIndexAttachmentSerializer(serializers.ModelSerializer):
    url = DocumentTypeHyperlinkedIdentifyField(
        view_name='rest_document_index_attachments-detail',
        lookup_field="pk",
        read_only=True)

    data_url = DocumentTypeHyperlinkedIdentifyField(
        view_name='attachment_data',
        lookup_field="pk",
        read_only=True)

    created_by = serializers.CharField(source="created_by.username")
    modified_by = serializers.CharField(source="modified_by.username")

    class Meta:
        model = models.DocumentIndexAttachment
        fields = (
            'id',
            'url',
            'data_url',
            'category',
            'content_type',
            'created_at',
            'modified_at',
            'created_by',
            'modified_by'
        )


class DocumentIndexSerializer(serializers.ModelSerializer):
    url = DocumentTypeHyperlinkedIdentifyField(
        view_name='rest_document_indices-detail',
        lookup_field="pk",
        read_only=True)

    containing_document_url = DocumentTypeHyperlinkedIdentifyField(
        view_name='rest_documents-detail',
        lookup_field="document__name",
        lookup_url_kwarg="name",
        read_only=True)

    containing_document_data_url = DocumentTypeHyperlinkedIdentifyField(
        view_name='document_data',
        lookup_field="document__name",
        lookup_url_kwarg="name",
        read_only=True)

    data_content_type = serializers.CharField(source="document.content_type")

    indexed_data = serializers.DictField(source="json")

    attachments_url = DocumentTypeHyperlinkedIdentifyField(
        view_name='rest_document_index_attachments-list',
        lookup_field="pk",
        lookup_url_kwarg="idx",
        read_only=True)

    attachments = DocumentIndexAttachmentSerializer(
        models.DocumentIndexAttachment.objects.defer('data'),
        many=True)

    class Meta:
        model = models.DocumentIndex
        fields = [
            'id',
            'url',
            'containing_document_url',
            'containing_document_data_url',
            'data_content_type',
            'indexed_data',
            'geometry',
            'attachments_url',
            'attachments'
        ]


class DocumentSerializer(serializers.ModelSerializer):
    data_url = DocumentTypeHyperlinkedIdentifyField(
        view_name='document_data',
        lookup_field="name",
        read_only=True)

    url = DocumentTypeHyperlinkedIdentifyField(
        view_name='rest_documents-detail',
        lookup_field="name",
        read_only=True)

    created_by = serializers.CharField(source="created_by.username")
    modified_by = serializers.CharField(source="modified_by.username")

    indices = DocumentIndexSerializer(many=True)

    class Meta:
        model = models.Document
        fields = [
            'id',
            'name',
            'url',
            'data_url',
            'document_type',
            'content_type',
            'filesize',
            'sha1',
            'created_at',
            'modified_at',
            'created_by',
            'modified_by',
            'indices'
        ]
