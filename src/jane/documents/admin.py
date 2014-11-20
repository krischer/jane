# -*- coding: utf-8 -*-

import base64

from django.contrib.gis import admin
from django.template.defaultfilters import filesizeformat

from jane.documents import models


class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "content_type"]

admin.site.register(models.DocumentType, DocumentTypeAdmin)


class DocumentRevisionInline(admin.TabularInline):
    model = models.DocumentRevision
    extra = 0
    readonly_fields = [f.name for f in models.DocumentRevision._meta.fields]


class DocumentAdmin(admin.ModelAdmin):
    list_display = ['pk', 'document_type', 'name']
    list_filter = ['document_type__name']
    inlines = [DocumentRevisionInline]

admin.site.register(models.Document, DocumentAdmin)


class DocumentRevisionAdmin(admin.GeoModelAdmin):
    list_display = ['pk', 'format_document_type', 'document', 'revision_number',
        'filename', 'format_filesize', 'created_at']
    list_filter = ['document__document_type', 'created_at']
    readonly_fields = [f.name for f in models.DocumentRevision._meta.fields]

    def format_document_type(self, obj):
        return obj.resource.resource_type.name
    format_document_type.short_description = 'Document type'
    format_document_type.admin_order_field = 'document__document_type__name'

    def format_filesize(self, obj):
        return filesizeformat(obj.filesize)
    format_filesize.short_description = 'File size'
    format_filesize.admin_order_field = 'filesize'

admin.site.register(models.DocumentRevision, DocumentRevisionAdmin)


class DocumentRevisionIndexAttachmentInline(admin.TabularInline):
    model = models.DocumentRevisionIndexAttachment
    extra = 0
    readonly_fields = \
        [f.name for f in models.DocumentRevisionIndexAttachment._meta.fields]


class DocumentRevisionIndexAdmin(admin.ModelAdmin):
    list_display = ['pk', 'format_document_type', 'format_document',
                    'created_at']
    list_filter = ['created_at',
                   'revision__document__document_type']
    inlines = [DocumentRevisionIndexAttachmentInline]

    def get_queryset(self, request):
        return super(DocumentRevisionIndexAdmin, self).get_queryset(request).\
            select_related('revision__document__document_type')

    def has_add_permission(self, request):
        # Nobody is allowed to add
        return False

    def format_document_type(self, obj):
        return obj.revision.document.document_type.name
    format_document_type.short_description = 'Document type'
    format_document_type.admin_order_field = \
            'revision__document__document_type__name'

    def format_document(self, obj):
        return obj.revision.document
    format_document.short_description = 'Document'
    format_document.admin_order_field = 'revision__document'

admin.site.register(models.DocumentRevisionIndex, DocumentRevisionIndexAdmin)


class DocumentRevisionIndexAttachmentAdmin(admin.ModelAdmin):
    list_display = ['pk', 'category', 'content_type',
                    'created_at', 'format_small_preview_image']
    list_filter = ['category']
    readonly_fields = ['pk', 'index', 'format_preview_image']

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

admin.site.register(models.DocumentRevisionIndexAttachment,
                    DocumentRevisionIndexAttachmentAdmin)
