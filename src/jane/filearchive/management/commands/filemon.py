# -*- coding: utf-8 -*-

import logging
from optparse import make_option
import os
import time

from django.core.management.base import BaseCommand
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.utils import platform

from jane.filearchive import tasks


# monkey - https://github.com/gorakhargosh/watchdog/issues/123
if platform.is_windows():
    import ctypes
    from watchdog.observers import winapi

    _HANDLE = ctypes.c_void_p
    _INVALID_HANDLE_VALUE = _HANDLE(-1).value

    winapi.INVALID_HANDLE_VALUE = _INVALID_HANDLE_VALUE


class EventHandler(LoggingEventHandler):

    def on_any_event(self, event):
        """
        Catch-all event handler.
        """
        data = {
            'is_directory': event.is_directory,
            'event_type': event.event_type,
            'src_path': event.src_path
        }
        if event.event_type == 'moved':
            data['dest_path'] = event.dest_path
        if not self.debug:
            tasks.filemon_event.delay(data)  # @UndefinedVariable
        else:
            tasks.filemon_event(data)


class Command(BaseCommand):
    args = 'path'
    help = "File monitor"  # @ReservedAssignment
    option_list = BaseCommand.option_list + (
        make_option('-d', '--debug',
            action='store_true',
            dest='debug',
            default=False,
            help='Debug'),
    )

    def handle(self, *args, **kwargs):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        try:
            path = args[0]
            if not os.path.isdir(path):
                raise
        except:
            path = os.path.curdir
        event_handler = EventHandler()
        event_handler.debug = kwargs['debug']
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
