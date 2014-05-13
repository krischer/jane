# -*- coding: utf-8 -*-

from rest_framework import serializers

from jane.documents import models


class AttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Attachment
        fields = ('id', 'category', 'content_type', 'created_at')


class RecordSerializer(serializers.ModelSerializer):
    attachments = AttachmentSerializer(many=True)
    indexed_data = serializers.CharField(source="json")

    class Meta:
        model = models.Record
        fields = ('id', 'document', 'indexed_data', 'attachments',
                  'created_at')
