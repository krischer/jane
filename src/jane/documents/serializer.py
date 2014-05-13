# -*- coding: utf-8 -*-

from rest_framework import serializers

from jane.documents import models


class IndexedValueAttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.IndexedValueAttachment
        fields = ('id', 'category', 'content_type', 'created_at')


class IndexedValueSerializer(serializers.ModelSerializer):
    attachments = IndexedValueAttachmentSerializer(many=True)
    indexed_data = serializers.CharField(source="json")

    class Meta:
        model = models.IndexedValue
        fields = ('id', 'indexed_data', 'attachments', 'created_at')
