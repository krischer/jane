# -*- coding: utf-8 -*-

import base64

from django.contrib.gis import admin
from django.template.defaultfilters import filesizeformat

from jane.documents import models


class ResourceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "content_type"]

admin.site.register(models.DocumentType, ResourceTypeAdmin)


class DocumentInline(admin.TabularInline):
    model = models.DocumentRevision
    extra = 0
    readonly_fields = [f.name for f in models.DocumentRevision._meta.fields]


class ResourceAdmin(admin.ModelAdmin):
    list_display = ['pk', 'document_type', 'name']
    list_filter = ['resource_type__name']
    inlines = [DocumentInline]

admin.site.register(models.Document, ResourceAdmin)


class DocumentAdmin(admin.GeoModelAdmin):
    list_display = ['pk', 'format_resource_type', 'document', 'revision',
        'filename', 'format_filesize', 'created_at']
    list_filter = ['resource__resource_type', 'created_at']
    readonly_fields = [f.name for f in models.DocumentRevision._meta.fields]

    def format_resource_type(self, obj):
        return obj.resource.resource_type.name
    format_resource_type.short_description = 'Document type'
    format_resource_type.admin_order_field = 'resource__resource_type__name'

    def format_filesize(self, obj):
        return filesizeformat(obj.filesize)
    format_filesize.short_description = 'File size'
    format_filesize.admin_order_field = 'filesize'

admin.site.register(models.DocumentRevision, DocumentAdmin)


class AttachmentInline(admin.TabularInline):
    model = models.DocumentRevisionAttachment
    extra = 0
    readonly_fields = [f.name for f in models.DocumentRevisionAttachment._meta.fields]


class RecordAdmin(admin.ModelAdmin):
    list_display = ['pk', 'format_resource_type', 'format_resource',
                    'created_at']
    list_filter = ['created_at', 'document__resource__resource_type']
    inlines = [AttachmentInline]

    def get_queryset(self, request):
        return super(RecordAdmin, self).get_queryset(request).\
            select_related('document__resource__resource_type')

    def has_add_permission(self, request):
        # Nobody is allowed to add
        return False

    def format_resource_type(self, obj):
        return obj.document.resource.resource_type.name
    format_resource_type.short_description = 'Document type'
    format_resource_type.admin_order_field = \
            'document__resource__resource_type__name'

    def format_resource(self, obj):
        return obj.document.resource
    format_resource.short_description = 'Document'
    format_resource.admin_order_field = 'document__resource'

admin.site.register(models.DocumentRevisionIndex, RecordAdmin)


class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['pk', 'category', 'content_type',
                    'created_at', 'format_small_preview_image']
    list_filter = ['category']
    readonly_fields = ['pk', 'document_revision_index', 'format_preview_image']

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

admin.site.register(models.DocumentRevisionAttachment, AttachmentAdmin)
