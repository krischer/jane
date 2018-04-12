# -*- coding: utf-8 -*-

import os

from django.db import transaction
from obspy.core import read
from obspy.core.preview import create_preview
from psycopg2.extras import DateTimeTZRange

from jane.exceptions import JaneWaveformTaskException

from . import models
from .utils import to_datetime


def process_file(filename):
    """
    Process a single waveform file.

    This is a bit more complex as it needs to update existing database
    objects and cannot just always create new ones. Otherwise the
    identifiers quickly reach very high numbers.
    """
    # Resolve symlinks and make a canonical simple path.
    filename = os.path.realpath(os.path.normpath(os.path.abspath(filename)))

    # ------------------------------------------------------------------------
    # Step 1: Get the file if it exists.
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

        # Nothing to do if nothing changed.
        if file.size == size and file.mtime == mtime and file.ctime == ctime:
            return

    # If it does not exist, create it in the next step.
    except models.File.DoesNotExist:
        file = None

    # ------------------------------------------------------------------------
    # Step 2: Read the file and perform a couple of sanity checks. Delete an
    #         eventually existing file.
    try:
        stream = read(filename)
    except Exception:
        # Delete if invalid file.
        if file is not None:
            file.delete()
        # Reraise the exception.
        raise

    if len(stream) == 0:
        msg = "'%s' is a valid waveform file but contains no actual data"
        raise JaneWaveformTaskException(msg % filename)
        # Delete if invalid file.
        if file is not None:
            file.delete()

    # Log channels for example are special as they have no sampling rate.
    if any(tr.stats.sampling_rate == 0 for tr in stream):
        # Make sure there is only one set of network, station,
        # location, and channel.
        ids = set(tr.id for tr in stream)
        if len(ids) != 1:
            # Delete if invalid file.
            if file is not None:
                file.delete()
            raise ValueError("File has a trace with sampling rate zero "
                             "and more then one different id.")

    # ------------------------------------------------------------------------
    # Step 3: Parse the file. Figure out which traces changed.
    #         Make sure it either gets created for a file or not.
    with transaction.atomic():
        # Create the file object if it does not exist.
        if file is None:
            path_obj = models.Path.objects.get_or_create(
                name=os.path.dirname(os.path.abspath(filename)))[0]
            models.File.objects. \
                filter(path=path_obj, name=os.path.basename(filename)). \
                delete()
            file = models.File.objects. \
                create(path=path_obj, name=os.path.basename(filename))

        # set format
        file.format = stream[0].stats._format

        # Collect information about all traces in a dictionary.
        traces_in_file = {}

        # Log channels for example are special as they have no sampling rate.
        if any(tr.stats.sampling_rate == 0 for tr in stream):
            starttime = min(tr.stats.starttime for tr in stream)
            endtime = max(tr.stats.endtime for tr in stream)
            if starttime == endtime:
                starttime += 0.001

            file.gaps = 0
            file.overlaps = 0
            file.save()

            try:
                quality = stream[0].stats.mseed.dataquality
            except AttributeError:
                quality = None

            traces_in_file[0] = {
                "starttime": starttime,
                "endtime": endtime,
                "network": stream[0].stats.network.upper(),
                "station": stream[0].stats.station.upper(),
                "location": stream[0].stats.location.upper(),
                "channel": stream[0].stats.channel.upper(),
                "sampling_rate": stream[0].stats.sampling_rate,
                "npts": sum(tr.stats.npts for tr in stream),
                "duration": endtime - starttime,
                "quality": quality,
                "preview_trace": None,
                "pos": 0}
        else:
            # get number of gaps and overlaps per file
            gap_list = stream.get_gaps()
            file.gaps = len([g for g in gap_list if g[6] >= 0])
            file.overlaps = len([g for g in gap_list if g[6] < 0])
            file.save()
            for pos, trace in enumerate(stream):
                try:
                    quality = trace.stats.mseed.dataquality
                except AttributeError:
                    quality = None

                # Preview is optional. For some traces, e.g. LOG channels it
                # does not work.
                try:
                    preview_trace = create_preview(trace, 60)
                except Exception:
                    preview_trace = None
                else:
                    preview_trace = list(map(float, preview_trace.data))

                traces_in_file[pos] = {
                    "starttime": trace.stats.starttime,
                    "endtime": trace.stats.endtime,
                    "network": trace.stats.network.upper(),
                    "station": trace.stats.station.upper(),
                    "location": trace.stats.location.upper(),
                    "channel": trace.stats.channel.upper(),
                    "sampling_rate": trace.stats.sampling_rate,
                    "npts": trace.stats.npts,
                    "duration": trace.stats.endtime - trace.stats.starttime,
                    "quality": quality,
                    "preview_trace": preview_trace,
                    "pos": pos}

        # Get all existing traces.
        for tr_db in models.ContinuousTrace.objects.filter(file=file):
            # Attempt to get the existing trace object.
            if tr_db.pos in traces_in_file:
                tr = traces_in_file[tr_db.pos]
                # Delete in the dictionary.
                del traces_in_file[tr_db.pos]

                tr_db.timerange = DateTimeTZRange(
                    lower=tr["starttime"].datetime,
                    upper=tr["endtime"].datetime)
                tr_db.network = tr["network"]
                tr_db.station = tr["station"]
                tr_db.location = tr["location"]
                tr_db.channel = tr["channel"]
                tr_db.sampling_rate = tr["sampling_rate"]
                tr_db.npts = tr["npts"]
                tr_db.duration = tr["duration"]
                tr_db.quality = tr["quality"]
                tr_db.preview_trace = tr["preview_trace"]
                tr_db.pos = tr["pos"]
                tr_db.save()

            # If it does not exist in the waveform file, delete it here as
            # it is (for whatever reason) no longer in the file..
            else:
                tr_db.delete()

        # Add remaining items.
        for tr in traces_in_file.values():
            tr_db = models.ContinuousTrace(
                file=file,
                timerange=DateTimeTZRange(
                    lower=tr["starttime"].datetime,
                    upper=tr["endtime"].datetime))
            tr_db.network = tr["network"]
            tr_db.station = tr["station"]
            tr_db.location = tr["location"]
            tr_db.channel = tr["channel"]
            tr_db.sampling_rate = tr["sampling_rate"]
            tr_db.npts = tr["npts"]
            tr_db.duration = tr["duration"]
            tr_db.quality = tr["quality"]
            tr_db.preview_trace = tr["preview_trace"]
            tr_db.pos = tr["pos"]
            tr_db.save()
