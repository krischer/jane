# -*- coding: utf-8 -*-

import io
import os

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from obspy.core import read
from obspy.core.preview import createPreview

from jane.exceptions import JaneException
from jane.filearchive import models


class JaneFilearchiveTaskException(JaneException):
    pass


@shared_task
def process_file(filename):
    """
    Process a single waveform file.
    """
    # Will raise a proper exception if not a waveform file.
    stream = read(filename)
    # get gap and overlap information
    gap_list = stream.getGaps()
    # merge channels and replace gaps/overlaps with 0 to prevent generation of
    # masked arrays
    stream.merge(fill_value=0)
    # build up dictionary of gaps and overlaps for easier lookup
    gap_dict = {}
    for gap in gap_list:
        id = '.'.join(gap[0:4])
        temp = {
            'gap': gap[6] >= 0,
            'starttime': gap[4].datetime,
            'endtime': gap[5].datetime,
            'samples': abs(gap[7])
        }
        gap_dict.setdefault(id, []).append(temp)

    if len(stream) == 0:
        msg = "'%s' is a valid waveform file but contains no actual data"
        raise JaneFilearchiveTaskException(msg % filename)

    # All or nothing. Use a transaction.
    with transaction.atomic():
        # make sure path and file objects exists
        path_obj = models.WaveformPath.objects.get_or_create(
            name=os.path.dirname(os.path.abspath(filename)))[0]
        file_obj = models.WaveformFile.objects.get_or_create(
            path=path_obj, name=os.path.basename(filename))[0]
        # set format
        file_obj.format = stream[0].stats._format
        file_obj.save()
        for trace in stream:
            channel_obj = models.WaveformChannel.objects.get_or_create(
                file=file_obj,
                starttime=trace.stats.starttime.datetime,
                endtime=trace.stats.endtime.datetime)[0]
            channel_obj.network = trace.stats.network
            channel_obj.station = trace.stats.station
            channel_obj.location = trace.stats.location
            channel_obj.channel = trace.stats.channel
            channel_obj.calib = trace.stats.calib
            channel_obj.sampling_rate = trace.stats.sampling_rate
            channel_obj.npts = trace.stats.npts

            # preview image
            plot = io.BytesIO()
            trace.plot(format="png", outfile=plot)
            plot.seek(0, 0)
            channel_obj.preview_image = plot.read()
            plot.close()

            # preview trace
            preview_trace = createPreview(trace, 30)
            channel_obj.preview_trace = preview_trace.data.dumps()

            channel_obj.save()

            # gaps
            for gap in gap_dict.get(trace.id, []):
                gap_obj = models.WaveformGap(channel=channel_obj, **gap)
                gap_obj.save()


def _format_return_value(event, message):
    return "Filemon event type: {event_type}, Result: {message}, Input: {" \
           "event}".format(event_type=event["event_type"], message=message,
                           event=str(event))


@shared_task
def filemon_event(event):
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
            process_file.delay(filename=src_path)
            return _format_return_value(event, "File sent to processing.")
        # Delete file object if file has been deleted.
        elif event_type == "deleted":
            try:
                models.WaveformFile.objects.get(path__name=src_folder,
                                        name=src_file).delete()
                return _format_return_value(event, "File deleted.")
            except ObjectDoesNotExist:
                return _format_return_value(event, "File already deleted.")
        elif event_type == "moved":
            dest_file = os.path.basename(event['dest_path'])
            dest_folder = os.path.dirname(event['dest_path'])

            # Nothing happened.
            if src_path == event["dest_path"]:
                return _format_return_value(event, "File not moved.")

            with transaction.atomic():
                dest_path_obj = models.WaveformPath.objects.get_or_create(
                    name=dest_folder)[0]
                dest_path_obj.save()

                src_file_obj = models.WaveformFile.objects.get(
                    path__name=src_folder, name=src_file)

                src_file_obj.name = dest_file
                src_file_obj.path = dest_path_obj
                src_file_obj.save()

            # Check if the src_path has files left in it. If not, try to
            # delete it.
            try:
                src_path_obj = models.WaveformPath.objects.get(name=src_folder)
            except ObjectDoesNotExist:
                return _format_return_value(event, "File moved, path already "
                                                   "deleted.")

            if src_path_obj.files.count() == 0:
                try:
                    src_path_obj.delete()
                except AssertionError:
                    return _format_return_value(event, "File moved, deleting "
                                                       "path failed.")
                return _format_return_value(event, "File moved, old path "
                                                   "deleted.")
            return _format_return_value(event, "File moved, path untouched.")
        # Should not happen.
        else:
            raise JaneFilearchiveTaskException(
                "Invalid watchdog event type: '%s'" % event_type)
    # Deal with directories.
    else:
        src_folder = os.path.abspath(event['src_path'])
        if event_type == "deleted":
            try:
                models.WaveformPath.objects.get(name=src_folder).delete()
                return _format_return_value(event, "Deleted path.")
            except ObjectDoesNotExist:
                return _format_return_value(event, "Failed deleting path.")
        elif event_type == "moved":
            # Only deal with it if the directory actually exists in the
            # database.
            try:
                path_obj = models.WaveformPath.objects.get(name=src_folder)
            except ObjectDoesNotExist:
                return _format_return_value(event, "File could not be moved.")
            # If it does, just update the path.
            path_obj.name = os.path.abspath(event['dest_path'])
            path_obj.save()
            return _format_return_value(event, "Moved path.")
        # Should not happen. Modified and created directories are not passed
        # to the task queue.
        else:
            raise JaneFilearchiveTaskException(
                "Invalid watchdog event type: '%s'" % event_type)


@shared_task
def index_path(path, debug=False):
    """
    Index given path
    """
    # convert to absolute path
    path = os.path.abspath(path)
    # delete all paths and files which start with path
    models.WaveformPath.objects.filter(name__startswith=path).delete()
    if debug:
        print("Purging %s ..." % (path))
    # indexing
    if debug:
        print("Indexing %s ..." % (path))
    for root, _, files in os.walk(path):
        # index each file
        for file in files:
            if debug:
                # direct
                print("  %s" % (file))
                process_file(os.path.join(root, file))
            else:
                # use celery
                process_file.delay(os.path.join(root, file))
