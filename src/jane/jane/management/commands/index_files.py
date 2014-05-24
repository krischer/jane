# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from jane.filearchive import tasks


class Command(BaseCommand):
    args = 'path path path'
    help = "Index files"  # @ReservedAssignment

    def handle(self, *args, **kwargs):  # @UnusedVariable
        if len(args) < 1:
            raise ValueError("path is required")

        # path(s)
        for path in args:
            tasks.index_path(path)
