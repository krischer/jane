# -*- coding: utf-8 -*-

import os

from celery import shared_task
from django.db import transaction
from obspy.core import read
from obspy.core.preview import createPreview
from psycopg2.extras import DateTimeTZRange


from jane.exceptions import JaneWaveformTaskException

from . import models
from .utils import to_datetime


@shared_task
def process_file(filename):
    """
    Process a single waveform file.
    """
    filename = os.path.normpath(os.path.abspath(filename))

    try:
        file = models.File.objects.get(
            path__name=os.path.dirname(filename),
            name=os.path.basename(filename))

        # This path is only reached if the file exists. Check size, mtime,
        # and ctime and if it all remains the same, return.
        stats = os.stat(filename)
        mtime = to_datetime(stats.st_mtime)
        ctime = to_datetime(stats.st_ctime)
        size = int(stats.st_size)
        if file.size == size and file.mtime == mtime and file.ctime == ctime:
            return
        else:
            # Not part of the transaction as we do want to delete if it is
            # no longer up-to-date even if it cannot be reindexed.
            file.delete()
    except models.File.DoesNotExist:
        pass

    # Make sure it either gets created for a file or not.
    with transaction.atomic():
        # Path object
        path_obj = models.Path.objects.get_or_create(
            name=os.path.dirname(os.path.abspath(filename)))[0]

        # Will raise a proper exception if not a waveform file.
        stream = read(filename)

        if len(stream) == 0:
            msg = "'%s' is a valid waveform file but contains no actual data"
            raise JaneWaveformTaskException(msg % filename)
        models.File.objects.filter(
            path=path_obj, name=os.path.basename(filename)).delete()
        file_obj = models.File.objects.create(
            path=path_obj, name=os.path.basename(filename))

        # set format
        file_obj.format = stream[0].stats._format

        # get number of gaps and overlaps per file
        gap_list = stream.getGaps()
        file_obj.gaps = len([g for g in gap_list if g[6] >= 0])
        file_obj.overlaps = len([g for g in gap_list if g[6] < 0])
        file_obj.save()

        pos = 0
        for trace in stream:
            trace_obj = models.ContinuousTrace(
                file=file_obj,
                timerange=DateTimeTZRange(
                    lower=trace.stats.starttime.datetime,
                    upper=trace.stats.endtime.datetime))
            trace_obj.network = trace.stats.network.upper()
            trace_obj.station = trace.stats.station.upper()
            trace_obj.location = trace.stats.location.upper()
            trace_obj.channel = trace.stats.channel.upper()
            trace_obj.sampling_rate = trace.stats.sampling_rate
            trace_obj.npts = trace.stats.npts
            trace_obj.duration = trace.stats.endtime - trace.stats.starttime
            try:
                trace_obj.quality = trace.stats.mseed.dataquality
            except AttributeError:
                pass

            preview_trace = createPreview(trace, 60)
            trace_obj.preview_trace = list(map(float, preview_trace.data))

            trace_obj.pos = pos
            trace_obj.save()
            pos += 1

@shared_task
def index_path(path, delete_files=False, celery_queue=None):
    """
    Index the given path.
    """
    if delete_files:
        print("Purging %s ..." % (path))
        # delete all paths and files which start with path
        models.Path.objects.filter(name__startswith=path).delete()

    for root, _, files in os.walk(path):
        print("Indexing %s ..." % (root))
        # index each file
        for file in files:
            filename = os.path.join(root, file)
            if celery_queue is None:
                print("\tIndexing file %s..." % filename)
                try:
                    process_file(filename)
                except Exception as e:
                    print("\tFailed to index files %s due to: %s" % (filename,
                                                                     str(e)))
            else:
                process_file.apply_async(args=[filename], queue=celery_queue)
