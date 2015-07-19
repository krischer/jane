# -*- coding: utf-8 -*-

import os

from django.db import transaction
from obspy.core import read
from obspy.core.preview import createPreview
from psycopg2.extras import DateTimeTZRange

from jane.exceptions import JaneWaveformTaskException

from . import models
from .utils import to_datetime


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

        # Log channels for example are special as they have no sampling rate.
        if any(tr.stats.sampling_rate == 0 for tr in stream):
            # Now make sure there is only one set of network, station,
            # location, and channel.
            ids = set(tr.id for tr in stream)
            if len(ids) != 1:
                raise ValueError("File has a trace with sampling rate zero "
                                 "and more then one different id.")

            starttime = min(tr.stats.starttime for tr in stream)
            endtime = min(tr.stats.endtime for tr in stream)
            if starttime == endtime:
                starttime += 0.001

            file_obj.save()
            trace_obj = models.ContinuousTrace(
                file=file_obj,
                timerange=DateTimeTZRange(
                    lower=starttime.timestamp,
                    upper=endtime.timestamp))
            trace_obj.network = stream[0].stats.network.upper()
            trace_obj.station = stream[0].stats.station.upper()
            trace_obj.location = stream[0].stats.location.upper()
            trace_obj.channel = stream[0].stats.channel.upper()
            trace_obj.sampling_rate = stream[0].stats.sampling_rate
            trace_obj.npts = sum(tr.stats.npts for tr in stream)
            trace_obj.duration = endtime - starttime
            try:
                trace_obj.quality = stream[0].stats.mseed.dataquality
            except AttributeError:
                pass

            trace_obj.pos = 0
            trace_obj.save()
            return

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

            # Preview is optional. For some traces, e.g. LOG channels it
            # does not work.
            try:
                preview_trace = createPreview(trace, 60)
            except:
                pass
            else:
                trace_obj.preview_trace = list(map(float, preview_trace.data))

            trace_obj.pos = pos
            trace_obj.save()
            pos += 1
