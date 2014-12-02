# -*- coding: utf-8 -*-

from functools import reduce
import operator
import os

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from obspy import Stream, read
from obspy.core.utcdatetime import UTCDateTime

from jane.waveforms.models import ContinuousTrace


@shared_task
def query_dataselect(networks, stations, locations, channels, starttime,
                     endtime, format, nodata, quality, minimumlength,
                     longestonly):
    """
    Process query and generate a combined waveform file
    """
    query = ContinuousTrace.objects
    # times
    starttime = UTCDateTime(starttime)
    query = query.filter(starttime__gte=starttime.datetime)
    endtime = UTCDateTime(endtime)
    query = query.filter(endtime__lte=endtime.datetime)
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
    # quality
    if quality:
        if quality in ['M', 'B']:
            query = query.filter(Q(quality='M') | Q(quality='B'))
        else:
            query = query.filter(quality=quality)
    # minimumlength
    if minimumlength:
        query = query.filter(duration__gte=minimumlength)

    # query
    results = query.all()
    if not results:
        # return nodata status code
        return nodata

    # build Stream object
    stream = Stream()
    for result in results:
        st = read(result.file.absolute_path, starttime=starttime,
                  endtime=endtime)
        tr = st[result.pos]
        # trim
        tr.trim(starttime, endtime)
        # append
        stream.append(tr)
        del st

    # get task_id
    task_id = query_dataselect.request.id or 'debug'
    path = os.path.join(settings.MEDIA_ROOT, 'fdsnws', 'dataselect',
                        task_id[0:2])
    # create path if not yet exists
    if not os.path.exists(path):
        os.makedirs(path)
    filename = os.path.join(path, task_id)
    # write file using task_id
    stream.write(filename, format=format.upper())
    return 200
