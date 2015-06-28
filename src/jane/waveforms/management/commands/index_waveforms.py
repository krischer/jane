# -*- coding: utf-8 -*-

import os

from django.core.management.base import BaseCommand

from ... import tasks


class Command(BaseCommand):
    help = "Index waveforms"

    def add_arguments(self, parser):
        parser.add_argument(
            '--celery', action='store_true',
            help="Distribute jobs to Celery's 'index_waveforms' queue. By "
                 "default all jobs will be run directly. Remember to have "
                 "celery workers with that queue running!")

        parser.add_argument(
            '--delete-files', action='store_true',
            help='Delete all files before indexing new ones. By default '
                'the indexer will just crawl all files and add new or '
                'changed ones. It will not delete anything. If true it will '
                'remove all files at or below the given path from the '
                'database before reindexing everything.')

        parser.add_argument("path", type=str, help="The path to index.")


    def handle(self, *args, **kwargs):  # @UnusedVariable
        path = os.path.abspath(kwargs["path"])

        # Run either in celery or direct.
        if kwargs["celery"]:
            print("Dispatched indexing path '%s' to celery." % path)
            tasks.index_path.apply_async(
                args=[path],
                kwargs={'delete_files': kwargs['delete_files'],
                        'celery_queue': 'index_waveforms'},
                queue='index_waveforms')
        else:
            tasks.index_path(path, delete_files=kwargs['delete_files'])
