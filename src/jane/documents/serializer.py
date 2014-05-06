from rest_framework import serializers


class IndexedValueAttachmentSerializer(serializers.Serializer):
    category = serializers.CharField()
    content_type = serializers.CharField()
    created_at = serializers.DateTimeField()


class IndexedValueSerializer(serializers.Serializer):
    attachments = IndexedValueAttachmentSerializer(many=True)
    created_at = serializers.DateTimeField()
    indexed_data = serializers.CharField(source="json")
