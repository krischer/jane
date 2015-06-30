# -*- coding: utf-8 -*-
import os

from django.core.management.base import BaseCommand

from ... import process_waveforms


class Command(BaseCommand):
    help = "Index waveforms"

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-files', action='store_true',
            help='Delete all files before indexing new ones. By default '
                'the indexer will just crawl all files and add new or '
                'changed ones. It will not delete anything. If true it will '
                'remove all files at or below the given path from the '
                'database before reindexing everything.')

        parser.add_argument("path", type=str, help="The path to index.")


    def handle(self, *args, **kwargs):  # @UnusedVariable
        process_waveforms.index_path(os.path.abspath(
            kwargs["path"]),
            delete_files=kwargs['delete_files'])
