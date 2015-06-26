# -*- coding: utf-8 -*-

import optparse

from django.core.management.base import BaseCommand

from jane.waveforms import tasks


class Command(BaseCommand):
    args = 'path path path'
    help = "Index waveforms"  # @ReservedAssignment

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug', '-d', action='store_true',
            default=False, help="Debug on")

    def handle(self, *args, **kwargs):  # @UnusedVariable
        if len(args) < 1:
            raise ValueError("path is required")

        # path(s)
        for path in args:
            tasks.index_path(path, debug=kwargs['debug'])
