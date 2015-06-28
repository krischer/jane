# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand

from ... import tasks


class Command(BaseCommand):
    args = 'path path path'
    help = "Index waveforms"  # @ReservedAssignment

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug', '-d', action='store_true',
            help="Debug on")

        parser.add_argument(
            '--delete-files', action='store_true',
            help="Delete all files before indexing new ones. By default "
                "the indexer will just crawl all files and add new one or "
                "changed ones. It will not delete anything.")

    def handle(self, *args, **kwargs):  # @UnusedVariable
        if len(args) < 1:
            raise ValueError("path is required")

        # path(s)
        for path in args:
            tasks.index_path(path, debug=kwargs['debug'],
                             delete_files=kwargs['delete_files'])