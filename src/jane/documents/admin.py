# -*- coding: utf-8 -*-

import base64

from django.conf.urls import url
from django.contrib.gis import admin
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.template.defaultfilters import filesizeformat

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

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
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
    readonly_fields = ["index", "json", "geometry"]

    edit_label = "View"

    def index(self, obj):
        if obj.id:
            opts = self.model._meta
            return "<a href='%s'>%s</a>" % (reverse(
                'admin:%s_%s_change' % (opts.app_label,
                                        opts.object_name.lower()),
                args=[obj.id]
            ), self.edit_label)
        else:
            return "(save to edit details)"
    index.allow_tags = True


class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'pk',
        'format_document_type',
        'name',
        'content_type',
        'format_filesize',
        'created_at',
        'modified_at',
        'created_by',
        'modified_by'
    ]
    list_filter = [
        'document_type',
        'created_at',
        'modified_at',
        'created_by',
        'modified_by'
    ]
    readonly_fields = [
        'document_type',
        'format_filesize',
        'sha1',
        'created_at',
        'created_by',
        'modified_at',
        'modified_by',
        'format_data'
    ]
    exclude = ['filesize']
    inlines = [DocumentIndexInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # defer data
        queryset = queryset.defer('data')
        # improve query performance for foreignkeys
        queryset = queryset.select_related('document_type', 'created_by',
                                           'modified_by')
        return queryset

    def format_document_type(self, obj):
        return obj.document_type.name

    format_document_type.short_description = 'Document type'
    format_document_type.admin_order_field = 'document_type__name'

    def format_filesize(self, obj):
        return filesizeformat(obj.filesize)
    format_filesize.short_description = 'File size'
    format_filesize.admin_order_field = 'filesize'

    def get_urls(self):
        urls = super(DocumentAdmin, self).get_urls()
        my_urls = [
            # Wrap in admin_view() to enforce permissions.
            url(r'^data/(?P<pk>[0-9]+)/$',
                view=self.admin_site.admin_view(self.data_view),
                name='documents_document_data'),
        ]
        return my_urls + urls

    def data_view(self, request, pk):
        document = self.get_object(request, pk)
        response = HttpResponse(document.data,
                                content_type=document.content_type)
        response['Content-Disposition'] = \
            'attachment; filename="%s"' % (document.name)
        return response

    def format_data(self, obj):
        url = reverse('admin:documents_document_data', kwargs={'pk': obj.pk})
        return '<a href="%s">Download</a>' % (url)
    format_data.short_description = 'Data'
    format_data.allow_tags = True

admin.site.register(models.Document, DocumentAdmin)


class DocumentIndexAttachmentInline(admin.TabularInline):
    model = models.DocumentIndexAttachment
    extra = 0
    readonly_fields = ["attachment", "category", "content_type",
                       "created_at", "format_small_preview_image"]

    edit_label = "View"

    def attachment(self, obj):
        if obj.id:
            opts = self.model._meta
            return "<a href='%s'>%s</a>" % (reverse(
                'admin:%s_%s_change' % (opts.app_label,
                                        opts.object_name.lower()),
                args=[obj.id]
            ), self.edit_label)
        else:
            return "(save to edit details)"
    attachment.allow_tags = True

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
        'pk',
        'format_document_type',
        'format_document']
    list_filter = ['document__document_type']
    # document needs to be readonly or raw_id to prevent performance issues
    readonly_fields = ['document']
    # force order of fields - readonly fields are usually displayed last
    fields = ['document', 'json', 'geometry']

    inlines = [DocumentIndexAttachmentInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # defer document data
        queryset = queryset.defer('document__data')
        # improve query performance for foreignkeys
        queryset = queryset.prefetch_related('document__document_type')
        return queryset

    def format_document_type(self, obj):
        return obj.document.document_type.name

    format_document_type.short_description = 'Document type'
    format_document_type.admin_order_field = \
        'document__document_type__name'

    def format_document(self, obj):
        return obj.document

    format_document.short_description = 'Document'
    format_document.admin_order_field = 'document'

admin.site.register(models.DocumentIndex, DocumentIndexAdmin)


class DocumentIndexAttachmentAdmin(admin.ModelAdmin):
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

admin.site.register(models.DocumentIndexAttachment,
                    DocumentIndexAttachmentAdmin)
