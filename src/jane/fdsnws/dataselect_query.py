# -*- coding: utf-8 -*-

from functools import reduce
import io
import operator

from django.db.models import Q
import obspy
from psycopg2._range import DateTimeTZRange

from jane.waveforms.models import ContinuousTrace, Restriction


def query_dataselect(networks, stations, locations, channels,
                     starttime, endtime, format, nodata, minimumlength,
                     longestonly, user=None):  # @UnusedVariable
    """
    Process query and generate a combined waveform file. Parameters are
    interpreted as in the FDSNWS definition. Results are written to fh. A
    returned numeric status code is interpreted as in the FDSNWS definition.
    """
    query = ContinuousTrace.objects

    # times
    starttime = obspy.UTCDateTime(starttime)
    endtime = obspy.UTCDateTime(endtime)

    # expand both by a tiny bit to also get samples that are exactly
    # at the boundary. The overlap query function does not get these
    # otherwise. The additional data is later cut again when trimming the
    # seismogram files.
    daterange = DateTimeTZRange((starttime - 0.1).datetime,
                                (endtime + 0.1).datetime)

    query = query.filter(timerange__overlap=daterange)
    # include networks
    if '*' not in networks:
        iterator = (Q(network__regex=r'^%s$' %
                      (v.replace('*', '.*').replace('?', '.')))
                    for v in networks if not v.startswith('-'))
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # exclude networks
    for network in networks:
        if network.startswith('-'):
            query = query.exclude(network=network[1:])
    # include stations
    if '*' not in stations:
        iterator = (Q(station__regex=r'^%s$' %
                      (v.replace('*', '.*').replace('?', '.')))
                    for v in stations if not v.startswith('-'))
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # exclude stations
    for station in stations:
        if station.startswith('-'):
            query = query.exclude(station=station[1:])
    # include locations
    if '*' not in locations:
        iterator = (Q(location__regex=r'^%s$' %
                      (v.replace('*', '.*').replace('?', '.')))
                    for v in locations if not v.startswith('-'))
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # exclude locations
    for location in locations:
        if location.startswith('-'):
            query = query.exclude(location=location[1:])
    # include channels
    if '*' not in channels:
        # include
        iterator = (Q(channel__regex=r'^%s$' %
                      (v.replace('*', '.*').replace('?', '.')))
                    for v in channels if not v.startswith('-'))
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # exclude channels
    for channel in channels:
        if channel.startswith('-'):
            query = query.exclude(channel=channel[1:])
    # minimumlength
    if minimumlength:
        query = query.filter(duration__gte=minimumlength)

    # restrictions
    if not user:
        restrictions = Restriction.objects.all()
    else:
        restrictions = Restriction.objects.exclude(users=user)
    for restriction in restrictions:
        query = query.exclude(network=restriction.network,
                              station=restriction.station)

    # Make sure the extraction function is only called once per file and
    # original SEED id. This means that some part of the filtering has to be
    # repeated in the data_streamer() function but it just much more
    # efficient.
    query = query\
        .order_by(
            "file__id", "original_network", "original_station",
            "original_location", "original_channel")\
        .distinct(
            "file__id", "original_network", "original_station",
            "original_location", "original_channel")

    results = query.all()

    if not results:
        return nodata

    return data_streamer(results, starttime, endtime, format)


def data_streamer(results, starttime, endtime, format):
    """
    Returns a iterator that will successively yield the requested data.

    It will yield once after each source file.
    """
    def iterator():
        for result in results:
            # Use time + sourcename to only read the required files.
            # Previous steps guarantee that this is only called once per
            # file and SEED id.
            st = obspy.read(
                result.file.absolute_path,
                starttime=starttime, endtime=endtime,
                sourcename="%s.%s.%s.%s" % (
                    result.original_network, result.original_station,
                    result.original_location, result.original_channel))
            for tr in st:
                tr.trim(starttime, endtime)
                # apply mappings if any
                tr.stats.network = result.network
                tr.stats.station = result.station
                tr.stats.location = result.location
                tr.stats.channel = result.channel
                # write trace
                with io.BytesIO() as fh:
                    tr.write(fh, format=format.upper())
                    fh.seek(0, 0)
                    yield fh.read()
            del st
    return iterator
