# -*- coding: utf-8 -*-

import base64

from django.conf.urls import url
from django.contrib.gis import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from jane.documents import models


class DocumentTypeAdmin(admin.ModelAdmin):
    """
    Everything is readonly as these models are filled with installed
    Jane plugins.
    """
    list_display = ["name", "definition", "indexer", "format_validators",
                    "format_retrieve_permissions", "format_upload_permissions"]
    readonly_fields = ["name", "definition", "indexer", "validators",
                       "retrieve_permissions", "upload_permissions"]

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        # disable ability to add rows
        return False

    def has_delete_permission(self, request, obj=None):  # @UnusedVariable
        # disable ability to delete rows
        return False

    def format_validators(self, obj):
        length = len(obj.validators.values())
        return "%i registered Validator(s)" % length

    def format_retrieve_permissions(self, obj):
        length = len(obj.retrieve_permissions.values())
        return "%i registered Retrieve Permission(s)" % length

    def format_upload_permissions(self, obj):
        length = len(obj.upload_permissions.values())
        return "%i registered Upload Permission(s)" % length

admin.site.register(models.DocumentType, DocumentTypeAdmin)


class DocumentIndexInline(admin.TabularInline):
    model = models.DocumentIndex
    extra = 0
    readonly_fields = ["format_index_id", "json", "geometry"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # defer data
        queryset = queryset.defer('document__data')
        return queryset

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        # disable ability to add rows
        return False


class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'format_document_type',
        'name',
        'content_type',
        'format_filesize',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by'
    ]
    list_filter = [
        'document_type',
        'created_at',
        'modified_at',
        'created_by__username',
    ]
    readonly_fields = [
        'id',
        'document_type',
        'format_filesize',
        'sha1',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'format_data'
    ]
    fieldsets = (
        ('', {
            'fields': [
                'id',
                'document_type',
                'name',
                'content_type',
                'sha1',
                'format_filesize',
                'format_data'
            ]
        }),
        ('History', {
            'fields': [
                'created_at',
                'created_by',
                'modified_at',
                'modified_by',
            ]
        }),
    )
    inlines = [DocumentIndexInline]
    search_fields = ['id', 'name']
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # defer data
        queryset = queryset.defer('data')
        # improve query performance for foreignkeys
        queryset = queryset.select_related('document_type', 'created_by',
                                           'modified_by')
        return queryset

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        # disable ability to add rows
        return False

    def get_urls(self):
        urls = [
            # Wrap in admin_view() to enforce permissions.
            url(r'^data/(?P<pk>[0-9]+)/$',
                view=self.admin_site.admin_view(self.download_view),
                name='documents_document_download'),
        ]
        return urls + super().get_urls()

    def download_view(self, request, pk):
        document = self.get_object(request, pk)
        response = HttpResponse(document.data,
                                content_type=document.content_type)
        response['Content-Disposition'] = \
            'attachment; filename="%s"' % (document.name)
        return response

    def format_data(self, obj):
        if obj.id is None:
            return
        url = reverse('admin:documents_document_download',
                      kwargs={'pk': obj.id})
        html = '<span class="object-tools"><a href="%s">Download</a></span>'
        return html % (url)
    format_data.short_description = 'Data'
    format_data.allow_tags = True

admin.site.register(models.Document, DocumentAdmin)


class DocumentIndexAttachmentInline(admin.TabularInline):
    model = models.DocumentIndexAttachment
    extra = 0
    list_display = [
        "format_attachment_id",
        "category",
        "content_type",
        "created_at",
        "created_by",
        "modified_by",
        "format_small_preview_image"
    ]
    readonly_fields = [
        "format_attachment_id",
        "category",
        "content_type",
        "created_at",
        "created_by",
        "modified_by",
        "format_small_preview_image"
    ]

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        # disable ability to add rows
        return False

    def has_delete_permission(self, request, obj=None):  # @UnusedVariable
        # disable ability to delete rows
        return False

    def format_small_preview_image(self, obj):
        if obj.content_type != "image/png":
            return b""
        data = base64.b64encode(obj.data)
        return '<img height="50" src="data:image/png;base64,%s" />' % (
            data.decode())
    format_small_preview_image.allow_tags = True
    format_small_preview_image.short_description = 'Preview'


class DocumentIndexAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'format_document_type',
        'format_document_id',
        'json'
    ]
    list_filter = ['document__document_type']
    # id needs to be readonly or raw_id to prevent performance issues
    readonly_fields = ['id']
    fieldsets = (
        ('', {
            'fields': [
                'id',
                'json',
                'geometry',
            ]
        }),
    )
    inlines = [DocumentIndexAttachmentInline]
    search_fields = ['id', 'document__name', 'json']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # improve query performance for foreignkeys
        queryset = queryset.select_related('document')
        # defer document data
        queryset = queryset.defer('document__data')
        # improve query performance for foreignkeys
        queryset = queryset.prefetch_related('document__document_type')
        return queryset

admin.site.register(models.DocumentIndex, DocumentIndexAdmin)


class DocumentIndexAttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'category',
        'content_type',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'format_small_preview_image'
    ]
    list_filter = [
        'category',
        'created_at',
        'modified_at',
        'created_by',
    ]
    readonly_fields = [
        'id',
        'format_preview_image',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'format_data',
    ]
    fieldsets = (
        ('', {
            'fields': [
                'id',
                'category',
                'content_type',
                'format_data',
            ]
        }),
        ('Preview', {
            'fields': [
                'format_preview_image',
            ]
        }),
        ('History', {
            'fields': [
                'created_at',
                'created_by',
                'modified_at',
                'modified_by',
            ]
        }),
    )
    search_fields = ['id']
    date_hierarchy = 'created_at'

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

    def get_urls(self):
        urls = [
            # Wrap in admin_view() to enforce permissions.
            url(r'^data/(?P<pk>[0-9]+)/$',
                view=self.admin_site.admin_view(self.download_view),
                name='documents_documentindexattachment_download'),
        ]
        return urls + super().get_urls()

    def download_view(self, request, pk):
        attachment = self.get_object(request, pk)
        response = HttpResponse(attachment.data,
                                content_type=attachment.content_type)
        response['Content-Disposition'] = \
            'attachment; filename="%d"' % (attachment.id)
        return response

    def format_data(self, obj):
        if obj.id is None:
            return
        url = reverse('admin:documents_documentindexattachment_download',
                      kwargs={'pk': obj.id})
        html = '<span class="object-tools"><a href="%s">Download</a></span>'
        return html % (url)
    format_data.short_description = 'Data'
    format_data.allow_tags = True

admin.site.register(models.DocumentIndexAttachment,
                    DocumentIndexAttachmentAdmin)
