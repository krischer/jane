# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.auth.models import Permission
from djcelery.models import TaskMeta


admin.site.register(Permission)


class TaskMetaAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'status', 'result', 'date_done', 'traceback')
    readonly_fields = ('task_id', 'status', 'result', 'date_done',
                       'traceback')

admin.site.register(TaskMeta, TaskMetaAdmin)
