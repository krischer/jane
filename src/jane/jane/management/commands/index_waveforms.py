# -*- coding: utf-8 -*-

import optparse

from django.core.management.base import BaseCommand

from jane.filearchive import tasks


class Command(BaseCommand):
    args = 'path path path'
    help = "Index waveforms"  # @ReservedAssignment
    option_list = BaseCommand.option_list + (
        optparse.make_option('-d', '--debug',
            action='store_true',
            dest='debug',
            default=False,
            help='Debug'),
    )

    def handle(self, *args, **kwargs):  # @UnusedVariable
        if len(args) < 1:
            raise ValueError("path is required")

        # path(s)
        for path in args:
            tasks.index_path(path, debug=kwargs['debug'])
