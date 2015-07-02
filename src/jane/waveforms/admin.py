# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.admin.filters import SimpleListFilter
from django.db.models.aggregates import Count

from jane.waveforms import models


class PathAdmin(admin.ModelAdmin):
    list_display = ['name', 'format_file_count', 'mtime', 'ctime']
    search_fields = ['name']
    date_hierarchy = 'mtime'
    readonly_fields = ['name', 'mtime', 'ctime']

    def get_queryset(self, request):  # @UnusedVariable
        return models.Path.objects.annotate(file_count=Count('files'))

    def format_file_count(self, obj):
        return obj.file_count
    format_file_count.short_description = '# Files'
    format_file_count.admin_order_field = 'file_count'

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        return False

admin.site.register(models.Path, PathAdmin)


class HasGapsFilter(SimpleListFilter):
    title = 'gaps'
    parameter_name = 'gaps'
    parameter_args = 0

    def lookups(self, request, model_admin):  # @UnusedVariable
        return (
            ('1', 'no gaps'),
            ('0', 'with gaps'),
        )

    def queryset(self, request, queryset):  # @UnusedVariable
        if self.value() == '1':
            return queryset.filter(gaps=self.parameter_args)
        if self.value() == '0':
            return queryset.exclude(gaps=self.parameter_args)
        return queryset


class HasOverlapsFilter(SimpleListFilter):
    title = 'overlaps'
    parameter_name = 'overlaps'
    parameter_args = 0

    def lookups(self, request, model_admin):  # @UnusedVariable
        return (
            ('1', 'no overlaps'),
            ('0', 'with overlaps'),
        )

    def queryset(self, request, queryset):  # @UnusedVariable
        if self.value() == '1':
            return queryset.filter(overlaps=self.parameter_args)
        if self.value() == '0':
            return queryset.exclude(overlaps=self.parameter_args)
        return queryset


class FileAdmin(admin.ModelAdmin):
    list_display = ['name', 'path', 'format', 'format_trace_count', 'gaps',
                    'overlaps', 'created_at']
    search_fields = ['name', 'path']
    date_hierarchy = 'created_at'
    readonly_fields = ['path', 'name', 'format', 'mtime', 'ctime', 'size',
                       'format_traces', 'gaps', 'overlaps', 'created_at']
    list_filter = ['format', HasGapsFilter, HasOverlapsFilter]
    fieldsets = (
        ('', {
            'fields': ('path', 'name', 'mtime', 'ctime', 'size', 'created_at')
        }),
        ('Stream', {
            'fields': ['format', 'format_traces', 'gaps', 'overlaps'],
        }),
    )

    def get_queryset(self, request):  # @UnusedVariable
        return models.File.objects.\
            annotate(trace_count=Count('traces'))

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        return False

    def format_trace_count(self, obj):
        return obj.trace_count
    format_trace_count.short_description = '# Traces'
    format_trace_count.admin_order_field = 'trace_count'

    def format_traces(self, obj):
        out = ''
        for trace in obj.traces.all():
            out += '%s<br />' % (trace)
        return out
    format_traces.allow_tags = True
    format_traces.short_description = 'Traces'

admin.site.register(models.File, FileAdmin)


class ContinuousTraceAdmin(admin.ModelAdmin):
    list_display = ['format_nslc', 'network', 'station', 'location', 'channel',
                    'starttime', 'endtime', 'sampling_rate', 'npts',
                    'quality']
    search_fields = ['network', 'station', 'location', 'channel']
    list_filter = ['network', 'station', 'location', 'channel',
                   'sampling_rate', 'quality']
    readonly_fields = [
        'file', 'format_path', 'pos', 'network', 'station', 'location',
        'channel', 'starttime', 'endtime', 'duration', 'sampling_rate', 'npts',
        'quality', 'preview_trace']

    exclude = ["timerange"]

    def starttime(self, obj):
        return obj.timerange.lower.isoformat() + "Z"

    def endtime(self, obj):
        return obj.timerange.upper.isoformat() + "Z"

    def has_add_permission(self, request, obj=None):  # @UnusedVariable
        return False

    def format_nslc(self, obj):
        return "%s.%s.%s.%s" % (obj.network, obj.station, obj.location,
                                obj.channel)
    format_nslc.short_description = 'SEED ID'

    def format_path(self, obj):
        return obj.file.path
    format_path.short_description = 'Path'

admin.site.register(models.ContinuousTrace, ContinuousTraceAdmin)


class MappingAdmin(admin.ModelAdmin):
    list_filter = ['network', 'station', 'location', 'channel']

admin.site.register(models.Mapping, MappingAdmin)


class RestrictionAdmin(admin.ModelAdmin):
    list_filter = ['network', 'station']
    list_display = ['network', 'station']

admin.site.register(models.Restriction, RestrictionAdmin)
