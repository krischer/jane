# -*- coding: utf-8 -*-

import collections
import copy
import csv
import fnmatch
from functools import reduce
import io
from obspy.core.util.geodetics import FlinnEngdahl
import operator
import os

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from lxml import etree
import obspy
from obspy.core.utcdatetime import UTCDateTime

from jane.documents.models import DocumentIndex
from jane.waveforms.models import ContinuousTrace, Restriction


JSON_QUERY_TEMPLATE_MAP = {
    int: "CAST(json->>'%s' AS INTEGER) %s %s",
    float: "CAST(json->>'%s' AS REAL) %s %s",
    str: "json->>'%s' %s '%s'",
    UTCDateTime: "CAST(json->>'%s' AS TIMESTAMP) %s TIMESTAMP '%s'"
}


# Define some constants for writing StationXML files.
SOFTWARE_MODULE = "Jane Alpha"
SOFTWARE_URI = "http://www.github.com/krischer/jane"
SCHEMA_VERSION = "1.0"

FG = FlinnEngdahl()


def _get_json_query(key, operator, type, value):
    return JSON_QUERY_TEMPLATE_MAP[type] % (key, operator, str(value))


def _format_time(value):
    return value.strftime("%Y-%m-%dT%H:%M:%S+00:00")


@shared_task
def query_stations(nodata, level, starttime=None, endtime=None,
                   network=None, station=None, location=None,
                   channel=None, minlatitude=None, maxlatitude=None,
                   minlongitude=None, maxlongitude=None):

    if starttime is not None:
        starttime = UTCDateTime(starttime)
    if endtime is not None:
        endtime = UTCDateTime(endtime)

    query = DocumentIndex.objects.filter(
        document__document_type="stationxml")

    where = []
    # XXX: Deal with non-existing start and end-dates!
    if starttime:
        where.append(
            _get_json_query("end_date", ">=", UTCDateTime, starttime))
    if endtime:
        where.append(
            _get_json_query("start_date", "<=", UTCDateTime, endtime))
    if minlatitude:
        where.append(
            _get_json_query("latitude", ">=", float, minlatitude))
    if maxlatitude:
        where.append(
            _get_json_query("latitude", "<=", float, maxlatitude))
    if minlongitude:
        where.append(
            _get_json_query("longitude", ">=", float, minlongitude))
    if maxlongitude:
        where.append(
            _get_json_query("longitude", "<=", float, maxlongitude))

    for key in ["network", "station", "location", "channel"]:
        argument = locals()[key]
        if argument and '*' not in argument:
            # Two percentage signs are needed (for escaping?)
            argument = [_i.replace("?", "_").replace("*", r"%%")
                        for _i in argument]
            n = ["json->>'%s' LIKE '%s'" % (key, _i) for _i in argument]
            where.append(" OR ".join(n))

    if where:
        query = query.extra(where=where)

    results = query.all()
    if not results:
        return nodata

    networks = assemble_network_elements(
        results, network, station, location, channel, starttime, endtime,
        level)

    nsmap = {None: "http://www.fdsn.org/xml/station/1"}
    root = etree.Element(
        "FDSNStationXML",
        attrib={"schemaVersion": SCHEMA_VERSION},
        nsmap=nsmap)

    # XXX: These things should be configurable.
    etree.SubElement(root, "Source").text = "Some Source"
    etree.SubElement(root, "Sender").text = "Some Sender"

    etree.SubElement(root, "Module").text = SOFTWARE_MODULE
    etree.SubElement(root, "ModuleURI").text = SOFTWARE_URI
    etree.SubElement(root, "Created").text = _format_time(UTCDateTime())

    root.extend(networks)

    # get task_id
    task_id = query_stations.request.id or 'debug'
    path = os.path.join(settings.MEDIA_ROOT, 'fdsnws', 'stations',
                        task_id[0:2])
    # create path if not yet exists
    if not os.path.exists(path):
        os.makedirs(path)
    filename = os.path.join(path, task_id + ".xml")
    print(filename)

    etree.ElementTree(root).write(filename, pretty_print=True,
                                  encoding="utf-8", xml_declaration=True)
    return 200


def assemble_network_elements(results, network, station, location, channel,
                              starttime, endtime, level):
    # Now the challenge is to find everything that is required and assemble
    # it in one new StationXML file.

    # First all files will be opened, an a hierarchical structure will be
    # created. This is probably faster in the average case where many
    # channels from only a few files are created. Memory usage should not
    # be an issue for the database size Jane is designed for.
    results = parse_stationxml_files(results)

    # Now filter once again based on the channels.
    chans = collections.OrderedDict()
    for ids, elem in results["channels"].items():
        # Check if any of the given condititions fail.
        n, s, l, c, st, et = ids

        # Filter out channels not in the time range.
        if starttime and starttime > et:
            continue
        if endtime and endtime > st:
            continue

        if network and "*" not in network:
            for net in network:
                if fnmatch.fnmatch(n, net):
                    break
            else:
                continue

        if station and "*" not in station:
            for sta in station:
                if fnmatch.fnmatch(s, sta):
                    break
            else:
                continue

        if location and "*" not in location:
            for loc in location:
                if fnmatch.fnmatch(l, loc):
                    break
            else:
                continue

        if channel and "*" not in channel:
            for cha in channel:
                if fnmatch.fnmatch(c, cha):
                    break
            else:
                continue
        chans[ids] = elem

    needed_networks = list(set([_i[0] for _i in chans.keys()]))
    needed_stations = list(set([(_i[0], _i[1]) for _i in chans.keys()]))

    final_networks = {_i: results["networks"][_i] for _i in needed_networks}
    # Remove all stations from the networks and the SelectedNumberStations
    # children.
    for code, network in final_networks.items():
        children = [_i for _i in network.getchildren() if (
            not _i.tag.endswith("}Station") and not _i.tag.endswith(
                "SelectedNumberStations"))]
        attrib = copy.deepcopy(network.attrib)
        network.clear()
        network.extend(children)
        network.attrib.update(attrib)
        etree.SubElement(network, "SelectedNumberStations").text = \
            str(len([_i for _i in needed_stations if _i[0] == code]))

    if level == "network":
        return list(final_networks.values())

    # Clean the stations.
    final_stations = {_i: results["stations"][_i] for _i in needed_stations}
    for code, station in final_stations.items():
        children = [_i for _i in station.getchildren() if (
            not _i.tag.endswith("}Channel") and not _i.tag.endswith(
                "SelectedNumberChannels"))]
        attrib = copy.deepcopy(station.attrib)
        station.clear()
        station.extend(children)
        station.attrib.update(attrib)
        etree.SubElement(station, "SelectedNumberChannels").text = \
            str(len([_i for _i in chans if (_i[0], _i[1]) == code]))
        # Assign to correct network.
        final_networks[code[0]].append(station)

    if level == "station":
        return list(final_networks.values())

    # Finally assign the channels.
    for idx, elem in chans.items():
        station = final_stations[(idx[0], idx[1])]
        station.append(elem)
        if level == "response":
            continue
        # Remove response if not desired.
        children = [
            _i for _i in elem.getchildren()
            if not _i.tag.endswith("}Response")]
        attrib = copy.deepcopy(elem.attrib)
        elem.clear()
        elem.extend(children)
        elem.attrib.update(attrib)

    return list(final_networks.values())


def parse_stationxml_files(results):
    parsed_docs = []
    final_results = {
        "networks": collections.OrderedDict(),
        "stations": collections.OrderedDict(),
        "channels": collections.OrderedDict()
    }
    for result in results:
        # The indexed document which contains the data.
        pk = result.pk
        if pk in parsed_docs:
            continue
        parsed_docs.append(pk)
        data = io.BytesIO(result.document.data)

        # Small state machine.
        net_state, sta_state = [None, None]

        ns = "http://www.fdsn.org/xml/station/1"
        network_tag = "{%s}Network" % ns
        station_tag = "{%s}Station" % ns
        channel_tag = "{%s}Channel" % ns

        tags = (network_tag, station_tag, channel_tag)
        context = etree.iterparse(data, events=("start", ), tag=tags)

        for _, elem in context:
            if elem.tag == channel_tag:
                channel = elem.get('code')
                location = elem.get('locationCode').strip()
                starttime = UTCDateTime(elem.get('startDate')).timestamp
                endtime = elem.get('endDate')
                if endtime:
                    endtime = UTCDateTime(endtime).timestamp
                final_results["channels"][(
                    net_state, sta_state, location, channel, starttime,
                    endtime)] = elem
            elif elem.tag == station_tag:
                sta_state = elem.get('code')
                final_results["stations"][(net_state, sta_state)] = elem
            elif elem.tag == network_tag:
                net_state = elem.get('code')
                final_results["networks"][net_state] = elem
    return final_results


def get_event_node(buffer, event_id):
    """
    Really fast way to extract the event node from QuakeML file with the
    correct event_id.
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
def query_event(nodata, orderby, format, starttime=None, endtime=None,
                minlatitude=None, maxlatitude=None, minlongitude=None,
                maxlongitude=None, mindepth_in_km=None, maxdepth_in_km=None,
                minmagnitude=None, maxmagnitude=None):

    if starttime is not None:
        starttime = UTCDateTime(starttime)
    if endtime is not None:
        endtime = UTCDateTime(endtime)

    query = DocumentIndex.objects.filter(
        document__document_type="quakeml")

    where = []

    # Definitions in the FDSNWS spec:
    #
    # Starttime: Limit to metadata epochs starting on or after the specified
    # start time.
    # Endtime: Limit to metadata epochs ending on or before the specified end
    # time.
    #
    # These don't really make sense and I don't think that's how they are
    # currently implemented in most services.
    # Starttime will make sure only channels whose end date is after the
    # given time remain.
    if starttime:
        where.append(
            _get_json_query("end_date", ">=", UTCDateTime, starttime))
    # Inverse is true for the stations.
    if endtime:
        where.append(
            _get_json_query("start_date", "<=", UTCDateTime, endtime))

    # Spatial constraints.
    if minlatitude:
        where.append(
            _get_json_query("latitude", ">=", float, minlatitude))
    if maxlatitude:
        where.append(
            _get_json_query("latitude", "<=", float, maxlatitude))
    if minlongitude:
        where.append(
            _get_json_query("longitude", ">=", float, minlongitude))
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
            _get_json_query("magnitude", "<=", float, maxmagnitude))

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

    # get task_id
    task_id = query_event.request.id or 'debug'
    path = os.path.join(settings.MEDIA_ROOT, 'fdsnws', 'events',
                        task_id[0:2])
    # create path if not yet exists
    if not os.path.exists(path):
        os.makedirs(path)
    filename = os.path.join(path, task_id + "." + format)

    if format == "xml":
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
            data = io.BytesIO(result.document.data)
            event = get_event_node(data, quakeml_id)
            if event is None:
                continue
            catalog_el.append(event)

        etree.ElementTree(root_el).write(filename, pretty_print=True,
                                         encoding="utf-8",
                                         xml_declaration=True)
    elif format == "text":

        header = ["EventID", "Time", "Latitude", "Longitude", "Depth/km",
                  "Author", "Catalog", "Contributor", "ContributorID",
                  "MagType", "Magnitude", "MagAuthor", "EventLocationName"]
        json_keys = ["quakeml_id", "origin_time", "latitude", "longitude",
                     "depth_in_m", None, None, None, None, "magnitude_type",
                     "magnitude", None]

        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter='|',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(header)
            for result in results:
                row = [result.json[_i] if _i is not None else ""
                       for _i in json_keys]
                # Convert depth to km.
                row[4] /= 1000.0
                row.append(FG.get_region(row[3], row[2]))
                writer.writerow(row)
    else:
        raise NotImplementedError
    return 200


@shared_task
def query_dataselect(networks, stations, locations, channels, starttime,
                     endtime, format, nodata, quality, minimumlength,
                     longestonly, username=None):
    """
    Process query and generate a combined waveform file
    """
    query = ContinuousTrace.objects
    # times
    starttime = UTCDateTime(starttime)
    endtime = UTCDateTime(endtime)
    query = query.filter(starttime__lte=endtime.datetime,
                         endtime__gte=starttime.datetime)
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

    # restrictions
    if not username:
        restrictions = Restriction.objects.all()
    else:
        user = User.objects.get(username=username)
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
