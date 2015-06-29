# -*- coding: utf-8 -*-

import logging
import os
import time

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import transaction
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.observers.polling import PollingObserverVFS
from watchdog.utils import platform

from jane.exceptions import JaneWaveformTaskException

from ... import models
from ...tasks import process_file

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
        # Do not deal with modified directories! Those are fired every time
        # a new file is added to a directory and are already caught by the
        # new files.
        # Also created directories are of no interest. The directory will be
        # added to the database as soon as a new file is added.
        if event.is_directory and event.event_type in ["created", "modified"]:
            return

        data = {
            'is_directory': event.is_directory,
            'event_type': event.event_type,
            'src_path': event.src_path
        }

        if event.event_type == 'moved':
            data['dest_path'] = os.path.abspath(event.dest_path)

        filemon_event(data, queue=self.queue)


class Command(BaseCommand):
    args = 'path'
    help = "File monitor"  # @ReservedAssignment

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug', '-d', action='store_true',
            help="Debug on")

        parser.add_argument(
            '--poll', action='store_true',
            help="Don't use the OS filesystem monitors, but poll the "
                 "filesystem in intervals.")

        parser.add_argument(
            '--polling-interval', type=int, default=60,
            help="Polling interval if --poll is used in seconds."
        )

        parser.add_argument(
            '--queue', type=str, default='monitor_waveforms',
            help='The name of the celery queue to use for the indexing. '
                 'Defaults to "monitor_waveforms".')

        parser.add_argument("path", type=str, help="The path to monitor.")


    def handle(self, *args, **kwargs):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        path = os.path.abspath(kwargs["path"])
        event_handler = EventHandler()
        event_handler.debug = kwargs['debug']
        event_handler.queue = kwargs['queue']
        if kwargs["poll"]:
            observer = PollingObserverVFS(
                stat=os.stat, listdir=os.listdir,
                polling_interval=kwargs["polling_interval"])
        else:
            observer = Observer()
        print("Monitoring '%s' ..." % path)
        print("Dispatching to celery queue '%s'." % kwargs["queue"])
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


def _format_return_value(event, message):
    return "Filemon event type: {event_type}, Result: {message}, Input: {" \
           "event}".format(event_type=event["event_type"], message=message,
                           event=str(event))


def filemon_event(event, queue):
    """
    Handle file monitor events
    """
    # Possible event types: created, deleted, modified, moved
    event_type = event['event_type']
    is_directory = event["is_directory"]

    # Assertions to gain trust in the async flow.
    assert event_type in ("created", "modified", "deleted", "moved")
    assert is_directory in (True, False)

    # Deal with files first.
    if is_directory is False:
        src_path = event['src_path']
        src_file = os.path.basename(src_path)
        src_folder = os.path.dirname(src_path)

        if event_type in ("created", "modified"):
            # New or modified file.
            process_file.apply_async(
                kwargs={"filename": src_path},
                queue=queue)
            print(_format_return_value(event, "File sent to processing."))
        # Delete file object if file has been deleted.
        elif event_type == "deleted":
            try:
                models.File.objects.get(path__name=src_folder,
                                        name=src_file).delete()
                print(_format_return_value(event, "File deleted."))
            except ObjectDoesNotExist:
                print(_format_return_value(event, "File already deleted."))
        elif event_type == "moved":
            dest_file = os.path.basename(event['dest_path'])
            dest_folder = os.path.dirname(event['dest_path'])

            # Nothing happened.
            if src_path == event["dest_path"]:
                print(_format_return_value(event, "File not moved."))

            with transaction.atomic():
                dest_path_obj = models.Path.objects.get_or_create(
                    name=dest_folder)[0]
                dest_path_obj.save()

                src_file_obj = models.File.objects.get(
                    path__name=src_folder, name=src_file)

                src_file_obj.name = dest_file
                src_file_obj.path = dest_path_obj
                src_file_obj.save()

            # Check if the src_path has files left in it. If not, try to
            # delete it.
            try:
                src_path_obj = models.Path.objects.get(name=src_folder)
            except ObjectDoesNotExist:
                print(_format_return_value(event, "File moved, path already "
                                           "deleted."))

            if src_path_obj.files.count() == 0:
                try:
                    src_path_obj.delete()
                except AssertionError:
                    print(_format_return_value(event, "File moved, deleting "
                                               "path failed."))
                print(_format_return_value(event, "File moved, old path "
                                           "deleted."))
            print(_format_return_value(event, "File moved, path untouched."))
        # Should not happen.
        else:
            raise JaneWaveformTaskException(
                "Invalid watchdog event type: '%s'" % event_type)
    # Deal with directories.
    else:
        src_folder = os.path.abspath(event['src_path'])
        if event_type == "deleted":
            try:
                models.Path.objects.get(name=src_folder).delete()
                print(_format_return_value(event, "Deleted path."))
            except ObjectDoesNotExist:
                print(_format_return_value(event, "Failed deleting path."))
        elif event_type == "moved":
            # Only deal with it if the directory actually exists in the
            # database.
            try:
                path_obj = models.Path.objects.get(name=src_folder)
            except ObjectDoesNotExist:
                print(_format_return_value(event, "File could not be moved."))
            # If it does, just update the path.
            path_obj.name = os.path.abspath(event['dest_path'])
            path_obj.save()
            print(_format_return_value(event, "Moved path."))
        # Should not happen. Modified and created directories are not passed
        # to the task queue.
        else:
            raise JaneWaveformTaskException(
                "Invalid watchdog event type: '%s'" % event_type)