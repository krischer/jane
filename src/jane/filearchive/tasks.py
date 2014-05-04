# -*- coding: utf-8 -*-

import os
import io

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from obspy.core import read

from jane.filearchive import models
from jane.exceptions import JaneException


class JaneFilearchiveTaskException(JaneException):
    pass


@shared_task
def process_file(filename):
    """
    Process a single waveform file.
    """
    # Will raise a proper exception if not a waveform file.
    stream = read(filename)

    if len(stream) == 0:
        msg = "'%s' is a valid waveform file but contains no actual data"
        raise JaneFilearchiveTaskException(msg % filename)

    # All or nothing. Use a transaction.
    with transaction.atomic():
        # make sure path and file objects exists
        path_obj = models.Path.objects.get_or_create(
            name=os.path.dirname(os.path.abspath(filename)))[0]
        file_obj = models.File.objects.get_or_create(
            path=path_obj, name=os.path.basename(filename))[0]
        # set format
        file_obj.format = stream[0].stats._format
        file_obj.save()
        for trace in stream:
            waveform_obj = models.Waveform.objects.get_or_create(file=file_obj,
                starttime=trace.stats.starttime.datetime,
                endtime=trace.stats.endtime.datetime)[0]
            waveform_obj.network = trace.stats.network
            waveform_obj.station = trace.stats.station
            waveform_obj.location = trace.stats.location
            waveform_obj.channel = trace.stats.channel
            waveform_obj.calib = trace.stats.calib
            waveform_obj.sampling_rate = trace.stats.sampling_rate
            waveform_obj.npts = trace.stats.npts

            plot = io.BytesIO()
            trace.plot(format="png", outfile=plot)
            plot.seek(0, 0)

            waveform_obj.preview_image = plot.read()
            waveform_obj.save()
    return



@shared_task
def filemon_event(event):
    """
    Handle file monitor events
    """
    # Possible event types: created, deleted, modified, moved
    event_type = event['event_type']

    # Deal with files first.
    if not event["is_directory"]:
        src_path = os.path.dirname(os.path.abspath(event['src_path']))
        src_file = os.path.basename(event['src_path'])
        if event_type in ("created", "modified"):
            # New or modified file.
            process_file.delay(filename=event['src_path'])
        # Deleted file.
        elif event_type == "deleted":
            try:
                models.File.objects.get(path__name=src_path,
                                        name=src_file).delete()
            except ObjectDoesNotExist:
                pass
        elif event_type == "moved":
            dest_path = os.path.dirname(event['dest_path'])
            dest_file = os.path.basename(event['dest_path'])

            # Nothing happened.
            if dest_path == src_path:
                return

            with transaction.atomic():
                dest_path_obj = models.Path.objects.get_or_create(
                    name=dest_path)[0]
                dest_path_obj.save()

                file_obj = models.File.objects.get(path__name=src_path,
                                                   name=src_file)

                file_obj.name = dest_file
                file_obj.path = dest_path_obj
                file_obj.save()
        # Should not happen.
        else:
            raise JaneFilearchiveTaskException(
                "Invalid watchdog event type: '%s'" % event_type)
    # Deal with directories.
    else:
        src_path = os.path.abspath(event['src_path'])
        if event_type == "deleted":
            try:
                models.Path.objects.get(name=src_path).delete()
            except ObjectDoesNotExist:
                pass
        elif event_type == "moved":
            # Only deal with it if the directory actually exists in the
            # database.
            try:
                path_obj = models.Path.objects.get(name=src_path)
            except ObjectDoesNotExist:
                return
            # If it does, just update the path.
            path_obj = models.Path.objects.get_or_create(name=src_path)[0]
            path_obj.name = os.path.abspath(
                os.path.dirname(event['dest_path']))
            path_obj.save()
        # Should not happen. Modified and created directories are not passed
        # to the task queue.
        else:
            raise JaneFilearchiveTaskException(
                "Invalid watchdog event type: '%s'" % event_type)


@shared_task
def index_path(path):
    """
    Index given path
    """
    # convert to absolute path
    path = os.path.abspath(path)
    try:
        # delete all paths and files which start with path
        models.Path.objects.filter(name__startswith=path).delete()
    except:
        return
    for root, _, files in os.walk(path):
        # index each file
        for file in files:
            process_file.delay(os.path.join(root, file))
