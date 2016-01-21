# -*- coding: utf-8 -*-

import collections
import copy
import io

from lxml import etree
from obspy import UTCDateTime

from django.conf import settings

import jane
from jane.documents.models import DocumentIndex


def _get_json_query(key, operator, type, value):
    return JSON_QUERY_TEMPLATE_MAP[type] % (key, operator, str(value))


def _format_time(value):
    return value.strftime("%Y-%m-%dT%H:%M:%S+00:00")


JSON_QUERY_TEMPLATE_MAP = {
    int: "CAST(json->>'%s' AS INTEGER) %s %s",
    float: "CAST(json->>'%s' AS REAL) %s %s",
    str: "json->>'%s' %s '%s'",
    UTCDateTime: "CAST(json->>'%s' AS TIMESTAMP) %s TIMESTAMP '%s'"
}


# Define some constants for writing StationXML files.
SOURCE = settings.JANE_FDSN_STATIONXML_SOURCE
SENDER = settings.JANE_FDSN_STATIONXML_SENDER
MODULE = "JANE WEB SERVICE: fdsnws-station | Jane version: %s" % \
    jane.__version__
SCHEMA_VERSION = "1.0"


def query_stations(fh, url, nodata, level, starttime=None, endtime=None,
                   startbefore=None, startafter=None, endbefore=None,
                   endafter=None, network=None, station=None, location=None,
                   channel=None, minlatitude=None, maxlatitude=None,
                   minlongitude=None, maxlongitude=None, latitude=None,
                   longitude=None, minradius=None, maxradius=None):
    """
    Process query and generate a combined StationXML or station text file.
    Parameters are interpreted as in the FDSNWS definition. Results are
    written to fh. A returned numeric status code is interpreted as in the
    FDSNWS definition.
    """
    if starttime is not None:
        starttime = UTCDateTime(starttime)
    if endtime is not None:
        endtime = UTCDateTime(endtime)
    if startbefore is not None:
        startbefore = UTCDateTime(startbefore)
    if startafter is not None:
        startafter = UTCDateTime(startafter)
    if endbefore is not None:
        endbefore = UTCDateTime(endbefore)
    if endafter is not None:
        endafter = UTCDateTime(endafter)

    query = DocumentIndex.objects.filter(
        document__document_type="stationxml")

    where = []
    if starttime:
        # If end_date is null it is assumed to be bigger.
        where.append(
            "((json->>'end_date') is null) OR (" +
            _get_json_query("end_date", ">=", UTCDateTime, starttime) + ")")
    if endtime:
        where.append(
            _get_json_query("start_date", "<=", UTCDateTime, endtime))
    if startbefore:
        where.append(
                _get_json_query("start_date", "<", UTCDateTime, startbefore))
    if startafter:
        where.append(
                _get_json_query("start_date", ">", UTCDateTime, startafter))
    if endbefore:
        # If end_date is null it is assumed to be bigger. We don't want that
        # here.
        where.append(
            "((json->>'end_date') is not null) AND (" +
            _get_json_query("end_date", "<", UTCDateTime, endbefore) + ")")
    if endafter:
        # If end_date is null it is assumed to be bigger.
        where.append(
            "((json->>'end_date') is null) OR (" +
            _get_json_query("end_date", ">", UTCDateTime, endafter) + ")")
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

    # Radial queries.
    if latitude:
        query = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="stationxml", queryset=query,
            central_latitude=latitude, central_longitude=longitude,
            min_radius=minradius, max_radius=maxradius)

    results = query.all()
    if not results:
        return nodata

    networks = assemble_network_elements(results=results, level=level)

    # XML headers are modelled after the IRIS headers.
    nsmap = {None: "http://www.fdsn.org/xml/station/1",
             "xsi": "http://www.w3.org/2001/XMLSchema-instance"}

    root = etree.Element(
        "FDSNStationXML",
        attrib={"schemaVersion": SCHEMA_VERSION,
                "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": (
                    "http://www.fdsn.org/xml/station/1 "
                    "http://www.fdsn.org/xml/station/fdsn-station-1.0.xsd")},
        nsmap=nsmap)

    # XXX: These things should be configurable.
    etree.SubElement(root, "Source").text = SOURCE
    etree.SubElement(root, "Sender").text = SENDER

    etree.SubElement(root, "Module").text = MODULE
    etree.SubElement(root, "ModuleURI").text = url
    etree.SubElement(root, "Created").text = _format_time(UTCDateTime())

    root.extend(networks)

    etree.ElementTree(root).write(fh, pretty_print=True,
                                  encoding="utf-8", xml_declaration=True)
    return 200


def assemble_network_elements(results, level):
    # Now the challenge is to find everything that is required and assemble
    # it in one new StationXML file.

    # First all files will be opened, an a hierarchical structure will be
    # created. This is probably faster in the average case where many
    # channels from only a few files are created. Memory usage should not
    # be an issue for the database size Jane is designed for.
    files = parse_stationxml_files(results)

    # All the required channel_ids
    channel_ids = set([(
        _i.json["network"], _i.json["station"], _i.json["location"],
        _i.json["channel"], _i.json["start_date"], _i.json["end_date"])
        for _i in results])

    # Now filter once again based on the channels.
    chans = collections.OrderedDict()
    for id, elem in files["channels"].items():
        if id not in channel_ids:
            continue
        chans[id] = elem

    # Remove no longer required networks and stations - should not happen
    # but better safe than sorry.
    needed_networks = list(set([_i[0] for _i in chans.keys()]))
    needed_stations = list(set([(_i[0], _i[1]) for _i in chans.keys()]))

    final_networks = {_i: files["networks"][_i] for _i in needed_networks}
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
    final_stations = {_i: files["stations"][_i] for _i in needed_stations}
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
                starttime = str(UTCDateTime(elem.get('startDate')))
                endtime = elem.get('endDate')
                if endtime:
                    endtime = str(UTCDateTime(endtime))
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
