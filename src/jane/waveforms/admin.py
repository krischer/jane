# -*- coding: utf-8 -*-

import base64

from django.contrib import admin
from django.db.models.aggregates import Count

from jane.waveforms import models, tasks


class PathAdmin(admin.ModelAdmin):
    list_display = ['name', 'format_file_count', 'mtime']
    search_fields = ['name']
    date_hierarchy = 'mtime'
    readonly_fields = ['name', 'mtime', 'ctime']
    actions = ['action_reindex']

    def get_queryset(self, request):  # @UnusedVariable
        return models.Path.objects.annotate(file_count=Count('files'))

    def action_reindex(self, request, queryset):  # @UnusedVariable
        for path in queryset.all():
            tasks.index_path.delay(path.name)  # @UndefinedVariable
        self.message_user(request, "Re-indexing has been started ...")
    action_reindex.short_description = "Re-index"

    def format_file_count(self, obj):
        return obj.file_count
    format_file_count.short_description = '# Files'
    format_file_count.admin_order_field = 'file_count'

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        return False

admin.site.register(models.Path, PathAdmin)


class FileAdmin(admin.ModelAdmin):
    list_display = ['name', 'path', 'format', 'format_trace_count', 'ctime',
                    'mtime']
    search_fields = ['name', 'path']
    date_hierarchy = 'mtime'
    readonly_fields = ['path', 'name', 'category', 'format', 'mtime', 'ctime',
        'size', 'format_traces']
    list_filter = ['format']
    fieldsets = (
        ('', {
            'fields': ('path', 'name', 'category', 'mtime', 'ctime', 'size')
        }),
        ('Stream', {
            'fields': ['format', 'format_traces'],
        }),
    )

    def get_queryset(self, request):  # @UnusedVariable
        return models.File.objects.\
            annotate(trace_count=Count('waveforms'))

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        return False

    def format_trace_count(self, obj):
        return obj.trace_count
    format_trace_count.short_description = '# Traces'
    format_trace_count.admin_order_field = 'trace_count'

    def format_traces(self, obj):
        out = ''
        for trace in obj.waveforms.all():
            out += '%s<br />' % (trace)
        return out
    format_traces.allow_tags = True
    format_traces.short_description = 'Traces'

admin.site.register(models.File, FileAdmin)


class ChannelAdmin(admin.ModelAdmin):
    list_display = ['format_nslc', 'network', 'station', 'location', 'channel',
        'starttime', 'endtime', 'sampling_rate', 'npts', 'format_gaps',
        'format_overlaps', 'format_small_preview_image']
    search_fields = ['network', 'station', 'location', 'channel']
    date_hierarchy = 'starttime'
    list_filter = ['network', 'station', 'location', 'channel',
        'sampling_rate']
    readonly_fields = ['file', 'format_path', 'network', 'station', 'location',
        'channel', 'starttime', 'endtime', 'sampling_rate', 'npts', 'calib',
        'preview_trace', 'format_preview_image']

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        return False

    def format_nslc(self, obj):
        return "%s.%s.%s.%s" % (obj.network, obj.station, obj.location,
                                obj.channel)
    format_nslc.short_description = 'SEED ID'

    def format_preview_image(self, obj):
        if not obj.preview_image:
            return
        data = base64.b64encode(obj.preview_image)
        return '<img height="250" src="data:image/png;base64,%s" />' % (
            data.decode())
    format_preview_image.allow_tags = True
    format_preview_image.short_description = 'Preview image'

    def format_small_preview_image(self, obj):
        if not obj.preview_image:
            return
        data = base64.b64encode(obj.preview_image)
        return '<img height="25" src="data:image/png;base64,%s" />' % (
            data.decode())
    format_small_preview_image.allow_tags = True
    format_small_preview_image.short_description = 'Preview image'

    def format_gaps(self, obj):
        return obj.gaps.filter(gap=True).count()
    format_gaps.allow_tags = True
    format_gaps.short_description = '# Gaps'

    def format_overlaps(self, obj):
        return obj.gaps.filter(gap=False).count()
    format_overlaps.allow_tags = True
    format_overlaps.short_description = '# Overlaps'

    def format_path(self, obj):
        return obj.file.path
    format_path.short_description = 'Path'

admin.site.register(models.Channel, ChannelAdmin)


class GapOverlapAdmin(admin.ModelAdmin):
    list_display = ['channel', 'gap', 'starttime', 'endtime', 'samples']
    readonly_fields = list_display

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        return False

admin.site.register(models.GapOverlap, GapOverlapAdmin)


class MappingAdmin(admin.ModelAdmin):
    list_filter = ['network', 'station', 'location', 'channel']

admin.site.register(models.Mapping, MappingAdmin)
