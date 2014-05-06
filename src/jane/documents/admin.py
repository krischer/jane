# -*- coding: utf-8 -*-

from django.contrib import admin

from jane.documents import models
import base64


class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "content_type"]

admin.site.register(models.ResourceType, ResourceTypeAdmin)


class ResourceAdmin(admin.ModelAdmin):
    list_display = ['pk', 'resource_type', 'name']
    list_filter = ['resource_type__name']

admin.site.register(models.Resource, ResourceAdmin)


class DocumentAdmin(admin.ModelAdmin):
    list_display = ['pk', 'resource', 'revision', 'filename', 'filesize',
        'sha1', 'created_at']
    list_filter = ['resource__resource_type__name', 'created_at']

admin.site.register(models.Document, DocumentAdmin)


class IndexedValueAdmin(admin.ModelAdmin):
    list_display = ['pk', 'json', 'created_at']
    list_filter = ['created_at']

admin.site.register(models.IndexedValue, IndexedValueAdmin)


class IndexedValueAttachmentAdmin(admin.ModelAdmin):
    list_display = ['pk', 'category', 'content_type',
                    'created_at', 'format_small_preview_image']
    list_filter = ['category']
    readonly_fields = ['pk', 'indexed_value', 'format_preview_image']

    def format_preview_image(self, obj):
        if obj.content_type != "image/png":
            return b""
        data = base64.b64encode(obj.data)
        return '<img height="500" src="data:image/png;base64,%s" />' % (
            data.decode())
    format_preview_image.allow_tags = True
    format_preview_image.short_description = 'Preview'

    def format_small_preview_image(self, obj):
        if obj.content_type != "image/png":
            return b""
        data = base64.b64encode(obj.data)
        return '<img height="50" src="data:image/png;base64,%s" />' % (
            data.decode())
    format_small_preview_image.allow_tags = True
    format_small_preview_image.short_description = 'Preview'

admin.site.register(models.IndexedValueAttachment, IndexedValueAttachmentAdmin)
