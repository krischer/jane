# -*- coding: utf-8 -*-

from functools import reduce
import io
from lxml import etree
from lxml.builder import E
import operator
import os

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from obspy import Stream, read
from obspy.core.utcdatetime import UTCDateTime

from jane.waveforms.models import ContinuousTrace
from jane.documents.models import DocumentRevisionIndex


JSON_QUERY_TEMPLATE_MAP = {
    int: "CAST(json->>'%s' AS INTEGER) %s %s",
    float: "CAST(json->>'%s' AS REAL) %s %s",
    str: "json->>'%s' %s '%s'",
    UTCDateTime: "CAST(json->>'%s' AS TIMESTAMP) %s TIMESTAMP '%s'"
}


def _get_json_query(key, operator, type, value):
    return JSON_QUERY_TEMPLATE_MAP[type] % (key, operator, str(value))


def get_event_node(buffer, event_id):
    """
    Really fast way to extract the event node with the correct event_id.
    """
    event_tag = "{http://quakeml.org/xmlns/bed/1.2}event"

    context = etree.iterparse(buffer, events=("start", ),
                              tag=(event_tag,))

    event = []
    for _, elem in context:
        if elem.attrib["publicID"] == event_id:
            event.append(elem)
            break
        while elem.getprevious() is not None:
            del elem.getparent()[0]
    if event:
        return event[0]
    return None


@shared_task
def query_event(nodata, orderby, starttime=None, endtime=None,
                minlatitude=None, maxlatitude=None, minlongitude=None,
                maxlongitude=None, mindepth_in_km=None, maxdepth_in_km=None,
                minmagnitude=None, maxmagnitude=None):
    query = DocumentRevisionIndex.objects.filter(
        revision__document__document_type="quakeml")

    where = []
    if starttime:
        where.append(
            _get_json_query("origin_time", ">=", UTCDateTime, starttime))
    if endtime:
        where.append(
            _get_json_query("origin_time", "<=", UTCDateTime, endtime))
    if minlatitude:
        where.append(
            _get_json_query("latitude", ">=", float, minlatitude))
    if maxlatitude:
        where.append(
            _get_json_query("latitude", "<=", float, maxlatitude))
    if minlongitude:
        where.append(
            _get_json_query("longitude", ">=", float, maxlongitude))
    if maxlongitude:
        where.append(
            _get_json_query("longitude", "<=", float, maxlongitude))
    if mindepth_in_km:
        where.append(
            _get_json_query("depth_in_m", ">=", float, mindepth_in_km * 1000))
    if maxdepth_in_km:
        where.append(
            _get_json_query("depth_in_m", "<=", float, maxdepth_in_km * 1000))
    if minmagnitude:
        where.append(
            _get_json_query("magnitude", ">=", float, minmagnitude))
    if maxmagnitude:
        where.append(
            _get_json_query("magnitude", "<=", float, minmagnitude))

    if where:
        query = query.extra(where=where)

    # Apply the ordering on the JSON fields.
    if orderby == "time":
        query = query \
            .extra(select={"origin_time": "json->>'origin_time'"}) \
            .extra(order_by=["-origin_time"])
    elif orderby == "time-asc":
        query = query \
            .extra(select={"origin_time": "json->>'origin_time'"}) \
            .extra(order_by=["origin_time"])
    elif orderby == "magnitude":
        query = query\
            .extra(select={"magnitude": "json->>'magnitude'"})\
            .extra(order_by=["-magnitude"])
    elif orderby == "magnitude-asc":
        query = query \
            .extra(select={"magnitude": "json->>'magnitude'"}) \
            .extra(order_by=["magnitude"])

    results = query.all()
    if not results:
        return nodata


    nsmap = {None: "http://quakeml.org/xmlns/bed/1.2",
             "ns0": "http://quakeml.org/xmlns/quakeml/1.2"}
    root_el = etree.Element('{%s}quakeml' % nsmap["ns0"],
                            nsmap=nsmap)
    catalog_el = etree.Element('eventParameters',
                               attrib={'publicID': "hmmm"})
    root_el.append(catalog_el)

    # Now things get a bit more interesting and this might actually require
    # a different approach to be fast enough.
    for result in results:
        quakeml_id = result.json["quakeml_id"]
        data = io.BytesIO(result.revision.data)
        event = get_event_node(data, quakeml_id)
        if event is None:
            continue
        catalog_el.append(event)

    # get task_id
    task_id = query_event.request.id or 'debug'
    path = os.path.join(settings.MEDIA_ROOT, 'fdsnws', 'events',
                        task_id[0:2])
    # create path if not yet exists
    if not os.path.exists(path):
        os.makedirs(path)
    filename = os.path.join(path, task_id + ".xml")

    etree.ElementTree(root_el).write(filename, pretty_print=True,
                                     encoding="utf-8", xml_declaration=True)
    return 200


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
