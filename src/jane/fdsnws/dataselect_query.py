# -*- coding: utf-8 -*-

from functools import reduce
import operator

from django.conf import settings
from django.db.models import Q
import obspy
from psycopg2._range import DateTimeTZRange

from jane.waveforms.models import ContinuousTrace, Restriction


def query_dataselect(fh, networks, stations, locations, channels,
                     starttime, endtime, format, nodata, minimumlength,
                     longestonly, username=None):
    """
    Process query and generate a combined waveform file. Parameters are
    interpreted as in the FDSNWS definition. Results are written to fh. A
    returned numeric status code is interpreted as in the FDSNWS definition.
    """
    query = ContinuousTrace.objects
    # times
    starttime = obspy.UTCDateTime(starttime)
    endtime = obspy.UTCDateTime(endtime)
    daterange = DateTimeTZRange(starttime.datetime, endtime.datetime)
    query = query.filter(timerange__overlap=daterange)
    # networks
    if '*' not in networks:
        iterator = (Q(network__like=v.replace('?', '_').replace('*', '%'))
                    for v in networks)
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # stations
    if '*' not in stations:
        iterator = (Q(station__like=v.replace('?', '_').replace('*', '%'))
                    for v in stations)
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # locations
    if '*' not in locations:
        iterator = (Q(location__like=v.replace('?', '_').replace('*', '%'))
                    for v in locations)
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # channels
    if '*' not in channels:
        iterator = (Q(channel__like=v.replace('?', '_').replace('*', '%'))
                    for v in channels)
        filter = reduce(operator.or_, iterator)
        query = query.filter(filter)
    # minimumlength
    if minimumlength:
        query = query.filter(duration__gte=minimumlength)

    # restrictions
    if not username:
        restrictions = Restriction.objects.all()
    else:
        user = settings.AUTH_USER_MODEL.objects.get(username=username)
        restrictions = Restriction.objects.exclude(users=user)
    for restriction in restrictions:
        query = query.exclude(network=restriction.network,
                              station=restriction.station)

    # query
    results = query.all()
    if not results:
        # return nodata status code
        return nodata

    # build Stream object
    stream = obspy.Stream()
    for result in results:
        st = obspy.read(result.file.absolute_path, starttime=starttime,
                        endtime=endtime)
        tr = st[result.pos]
        # trim
        tr.trim(starttime, endtime)
        # append
        stream.append(tr)
        del st

    # Write to file handler which is a BytesIO object.
    stream.write(fh, format=format.upper())
    return 200