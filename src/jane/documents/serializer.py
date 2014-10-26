# -*- coding: utf-8 -*-

from rest_framework import serializers, pagination
from rest_framework.reverse import reverse
from rest_framework_gis.serializers import GeoModelSerializer

from jane.documents import models


class AttachmentSerializer(serializers.ModelSerializer):

    url = serializers.URLField(source='pk', read_only=True)

    def transform_url(self, obj, value):
        request = self.context.get('request')
        rt_name = self.context.get('resource_type_name')
        index_id = obj.record.pk
        return reverse('attachment_detail', args=[rt_name, index_id, value],
                       request=request)

    class Meta:
        model = models.Attachment
        fields = ('id', 'url', 'category', 'content_type', 'created_at')


class RecordSerializer(GeoModelSerializer):

    attachments = AttachmentSerializer(many=True)
    indexed_data = serializers.CharField(source="json")
    url = serializers.URLField(source='pk', read_only=True)

    def transform_url(self, obj, value):
        request = self.context.get('request')
        rt_name = self.context.get('resource_type_name')
        return reverse('record_detail', args=[rt_name, value], request=request)

    class Meta:
        model = models.Record
        fields = ('id', 'url', 'document', 'indexed_data', 'geometry',
                  'attachments', 'created_at')


class PaginatedRecordSerializer(pagination.PaginationSerializer):
    """
    Serializes page objects of record querysets.
    """
    pages = serializers.Field(source='paginator.num_pages')

    class Meta:
        object_serializer_class = RecordSerializer
