# -*- coding: utf-8 -*-

import collections
import copy
import csv
import io

from lxml import etree
from obspy import UTCDateTime

from django.conf import settings
from django.shortcuts import get_object_or_404

import jane
from jane.documents.models import DocumentIndex, DocumentType
from jane.jane.utils import _queryset_filter_jsonfield_isnull


def _format_time(value):
    return value.strftime("%Y-%m-%dT%H:%M:%S+00:00")


# Define some constants for writing StationXML files.
SOURCE = settings.JANE_FDSN_STATIONXML_SOURCE
SENDER = settings.JANE_FDSN_STATIONXML_SENDER
MODULE = "JANE WEB SERVICE: fdsnws-station | Jane version: %s" % \
    jane.__version__
SCHEMA_VERSION = "1.0"


class StationStats(object):
    """
    Class to retrieve global station statistics.

    Might be worthwhile to use a cache here.
    """
    def __init__(self):
        res_type = get_object_or_404(DocumentType, name="stationxml")
        queryset = DocumentIndex.objects. \
            filter(document__document_type=res_type)
        self.data = [_i.json for _i in queryset]

    def stations_for_network(self, network):
        return len(set([_i["station"] for _i in self.data
                        if _i["network"] == network]))

    def channels_for_station(self, network, station):
        """
        Returns the number of channel epochs for a station.

        Iris also defines one channel as one channel epoch.
        """
        return len([_i["channel"] for _i in self.data
                    if _i["network"] == network and
                    _i["station"] == station])

    def _get_temp_extend(self, times):
        start_date = min([_i[0] for _i in times])
        _ed = [_i[1] for _i in times]
        if None in _ed:
            end_date = None
        else:
            end_date = max(_ed)
        return start_date, end_date

    def temporal_extent_of_network(self, network):
        times = [(_i["start_date"], _i["end_date"]) for _i in self.data if
                 _i["network"] == network]
        return self._get_temp_extend(times)

    def temporal_extent_of_station(self, network, station):
        times = [(_i["start_date"], _i["end_date"]) for _i in self.data if
                 _i["network"] == network and _i["station"] == station]
        return self._get_temp_extend(times)

    def creation_date_for_station(self, network, station):
        """
        Get the earliest creation date for a station.
        """
        times = [_i["station_creation_date"] for _i in self.data
                 if _i["station_creation_date"] is not None]
        if times:
            return min(times)
        return None


def query_stations(fh, url, nodata, level, format, user, starttime=None,
                   endtime=None, startbefore=None, startafter=None,
                   endbefore=None, endafter=None, network=None, station=None,
                   location=None, channel=None, minlatitude=None,
                   maxlatitude=None, minlongitude=None, maxlongitude=None,
                   latitude=None, longitude=None, minradius=None,
                   maxradius=None):
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

    if starttime:
        # If end_date is null it is assumed to be bigger.
        query = (query.filter(json__end_date__gte=starttime.isoformat()) |
                 _queryset_filter_jsonfield_isnull(query, path=['end_date'],
                                                   isnull=True)).distinct()
    if endtime:
        query = query.filter(json__start_date__lte=endtime.isoformat())
    if startbefore:
        query = query.filter(json__start_date__lte=startbefore.isoformat())
    if startafter:
        query = query.filter(json__start_date__gt=startafter.isoformat())
    if endbefore:
        # If end_date is null it is assumed to be bigger. We don't want that
        # here.
        query = (query.filter(json__end_date__lt=endbefore.isoformat()) &
                 _queryset_filter_jsonfield_isnull(query, path=['end_date'],
                                                   isnull=False)).distinct()
    if endafter:
        # If end_date is null it is assumed to be bigger.
        query = (query.filter(json__end_date__gt=endafter.isoformat()) |
                 _queryset_filter_jsonfield_isnull(query, path=['end_date'],
                                                   isnull=True)).distinct()
    if minlatitude is not None:
        query = query.filter(json__latitude__gte=minlatitude)
    if maxlatitude is not None:
        query = query.filter(json__latitude__lte=maxlatitude)
    if minlongitude is not None:
        query = query.filter(json__longitude__gte=minlongitude)
    if maxlongitude is not None:
        query = query.filter(json__longitude__lte=maxlongitude)

    for key in ["network", "station", "location", "channel"]:
        argument = locals()[key]
        if argument is not None:
            for argument_ in argument:
                value = argument_
                if value.startswith('-'):
                    value = value[1:]
                    query_method = query.exclude
                else:
                    query_method = query.filter
                method = 'exact'
                # Possible wildcards.
                if "*" in value or "?" in value:
                    value = value.replace("*", ".*").replace("?", ".")
                    method = 'iregex'
                # the regex field lookup on JSON fields suffers from a
                # bug on Django 1.9, see django/django#6929.
                # We patch django's json field on django <1.11 in
                # jane/__init__.py
                query = query & query_method(**{
                    'json__{}__{}'.format(key, method): value})
            query = query.distinct()

    # Radial queries - also apply the per-user filtering right here!
    if latitude is not None:
        query = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="stationxml", queryset=query,
            central_latitude=latitude, central_longitude=longitude,
            min_radius=minradius, max_radius=maxradius, user=user)
    else:
        doctype = get_object_or_404(DocumentType, name="stationxml")
        query = DocumentIndex.objects.apply_retrieve_permission(
            document_type=doctype, queryset=query, user=user)

    results = query.all()
    if not results:
        return nodata

    # Some things require global statistics.
    stats = StationStats()

    if format == "xml":
        # XML headers are modelled after the IRIS headers.
        nsmap = {None: "http://www.fdsn.org/xml/station/1",
                 "xsi": "http://www.w3.org/2001/XMLSchema-instance"}

        root = etree.Element(
            "FDSNStationXML", attrib={
                "schemaVersion": SCHEMA_VERSION,
                "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation": (
                    "http://www.fdsn.org/xml/station/1 "
                    "http://www.fdsn.org/xml/station/fdsn-station-1.0.xsd")},
                nsmap=nsmap)

        etree.SubElement(root, "Source").text = SOURCE
        etree.SubElement(root, "Sender").text = SENDER

        etree.SubElement(root, "Module").text = MODULE
        etree.SubElement(root, "ModuleURI").text = url
        etree.SubElement(root, "Created").text = _format_time(UTCDateTime())

        # Channel or response levels require parsing all XML files. This is
        # slow but most people will probably only request a limited number
        # of files in this fashion.
        if level in ["channel", "response"]:
            networks = assemble_network_elements(results=results, level=level,
                                                 stats=stats)
            root.extend(networks)
        elif level in ("station", "network"):
            # Find unique networks - keep one element per network.
            networks = {}
            for _i in results:
                network = _i.json["network"]
                station = _i.json["station"]

                if network not in networks:
                    networks[network] = {}

                if station in networks[network]:
                    continue

                networks[network][station] = _i.json

            # Sort alphabetically to be more predictable.
            all_networks = sorted(networks.keys())
            for net_code in all_networks:
                # Get information about the very first channel is used to
                # derive the rest of the station information.
                value = next(iter(networks[net_code].values()))

                t = stats.temporal_extent_of_network(net_code)

                attrib = {}
                attrib["code"] = net_code
                attrib["startDate"] = t[0]
                if t[1] is not None:
                    attrib["endDate"] = t[1]

                net_elem = etree.SubElement(root, "Network", attrib=attrib)

                etree.SubElement(net_elem, "Description").text = \
                    value["network_name"]

                etree.SubElement(net_elem, "TotalNumberStations").text = \
                    str(stats.stations_for_network(net_code))

                if level == "network":
                    _c = "0"
                elif level == "station":
                    _c = str(len(networks[net_code]))
                etree.SubElement(net_elem, "SelectedNumberStations").text = _c

                # Also add station information if required.
                if level != "station":
                    continue

                all_stations = sorted(networks[net_code].keys())
                for sta_code in all_stations:
                    value = networks[net_code][sta_code]

                    t = stats.temporal_extent_of_station(net_code, sta_code)

                    attrib = {}
                    attrib["code"] = sta_code
                    attrib["startDate"] = t[0]
                    if t[1] is not None:
                        attrib["endDate"] = t[1]

                    sta_elem = etree.SubElement(net_elem, "Station",
                                                attrib=attrib)

                    etree.SubElement(sta_elem, "Latitude").text = \
                        str(value["latitude"])
                    etree.SubElement(sta_elem, "Longitude").text = \
                        str(value["longitude"])
                    etree.SubElement(sta_elem, "Elevation").text = \
                        str(value["elevation_in_m"])

                    site = etree.SubElement(sta_elem, "Site")
                    etree.SubElement(site, "Name").text = value["station_name"]

                    etree.SubElement(sta_elem, "CreationDate").text = \
                        stats.creation_date_for_station(net_code, sta_code)

                    etree.SubElement(sta_elem, "TotalNumberChannels").text = \
                        str(stats.channels_for_station(net_code, sta_code))
                    etree.SubElement(sta_elem, "SelectedNumberChannels").text \
                        = "0"

        else:
            raise NotImplementedError

        etree.ElementTree(root).write(fh, pretty_print=True,
                                      encoding="utf-8", xml_declaration=True)
    elif format == "text":

        class FDSNDialiect(csv.Dialect):
            delimiter = "|"
            quoting = csv.QUOTE_MINIMAL
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\n"

        if level == "network":
            # Find unique networks - keep one element per network.
            networks = collections.OrderedDict()
            for _i in results:
                network = _i.json["network"]
                if network in networks:
                    continue
                networks[network] = _i.json

            field_names = ["Network", "Description", "StartTime", "EndTime",
                           "TotalStations"]

            with io.StringIO() as buf:
                buf.write("#")
                writer = csv.DictWriter(buf, fieldnames=field_names,
                                        restval="", dialect=FDSNDialiect)
                writer.writeheader()

                for key, value in networks.items():
                    t = stats.temporal_extent_of_network(key)
                    writer.writerow({
                        "Network": value["network"],
                        "Description": value["network_name"],
                        "StartTime": t[0],
                        "EndTime": t[1],
                        "TotalStations": stats.stations_for_network(key)})

                buf.seek(0, 0)
                fh.write(buf.read().encode())

        elif level == "station":
            # Find unique networks - keep one element per network.
            stations = collections.OrderedDict()
            for _i in results:
                network = _i.json["network"]
                station = _i.json["station"]
                if (network, station) in stations:
                    continue
                stations[(network, station)] = _i.json

            field_names = ["Network", "Station", "Latitude", "Longitude",
                           "Elevation", "SiteName", "StartTime", "EndTime"]

            with io.StringIO() as buf:
                buf.write("#")
                writer = csv.DictWriter(buf, fieldnames=field_names,
                                        restval="", dialect=FDSNDialiect)
                writer.writeheader()

                for key, value in stations.items():
                    t = stats.temporal_extent_of_station(key[0], key[1])
                    writer.writerow({
                        "Network": value["network"],
                        "Station": value["station"],
                        "Latitude": value["latitude"],
                        "Longitude": value["longitude"],
                        "Elevation": value["elevation_in_m"],
                        "SiteName": value["station_name"],
                        "StartTime": t[0],
                        "EndTime": t[1]})

                buf.seek(0, 0)
                fh.write(buf.read().encode())

        elif level == "channel":
            field_names = ["Network", "Station", "Location", "Channel",
                           "Latitude", "Longitude", "Elevation", "Depth",
                           "Azimuth", "Dip", "SensorDescription", "Scale",
                           "ScaleFreq", "ScaleUnits", "SampleRate",
                           "StartTime", "EndTime"]

            with io.StringIO() as buf:
                buf.write("#")
                writer = csv.DictWriter(buf, fieldnames=field_names,
                                        restval="", dialect=FDSNDialiect)
                writer.writeheader()

                for _i in results:
                    value = _i.json
                    writer.writerow({
                        "Network": value["network"],
                        "Station": value["station"],
                        "Location": value["location"],
                        "Channel": value["channel"],
                        "Latitude": value["latitude"],
                        "Longitude": value["longitude"],
                        "Elevation": value["elevation_in_m"],
                        "Depth": value["depth_in_m"],
                        "Azimuth": value["azimuth"],
                        "Dip": value["dip"],
                        "SensorDescription": value["sensor_type"],
                        "Scale": value["total_sensitivity"],
                        "ScaleFreq": value["sensitivity_frequency"],
                        "ScaleUnits": value["units_after_sensitivity"],
                        "SampleRate": value["sample_rate"],
                        "StartTime": value["start_date"],
                        "EndTime": value["end_date"]})

                buf.seek(0, 0)
                fh.write(buf.read().encode())
        else:
            raise NotImplementedError
    else:
        raise NotImplementedError
    return 200


def assemble_network_elements(results, level, stats):
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
            not _i.tag.endswith("}Station") and
            not _i.tag.endswith("SelectedNumberStations") and
            not _i.tag.endswith("TotalNumberStations"))]
        attrib = copy.deepcopy(network.attrib)

        # Derive start and end-dates from the channels.
        if "startDate" in attrib:
            del attrib["startDate"]
        if "endDate" in attrib:
            del attrib["endDate"]
        sd, ed = stats.temporal_extent_of_network(code)
        attrib["startDate"] = sd
        if ed is not None:
            attrib["endDate"] = ed

        network.clear()
        network.extend(children)
        network.attrib.update(attrib)

        etree.SubElement(network, "TotalNumberStations").text = \
            str(stats.stations_for_network(code))

        # No stations selected for level == 'network'
        if level != "network":
            etree.SubElement(network, "SelectedNumberStations").text = \
                str(len([_i for _i in needed_stations if _i[0] == code]))
        else:
            etree.SubElement(network, "SelectedNumberStations").text = "0"

    if level == "network":
        return list(final_networks.values())

    # Clean the stations.
    final_stations = {_i: files["stations"][_i] for _i in needed_stations}
    for code, station in final_stations.items():
        children = [_i for _i in station.getchildren() if (
            not _i.tag.endswith("}Channel") and
            not _i.tag.endswith("SelectedNumberChannels") and
            not _i.tag.endswith("TotalNumberChannels"))]
        attrib = copy.deepcopy(station.attrib)

        # Derive start and end-dates from the channels.
        if "startDate" in attrib:
            del attrib["startDate"]
        if "endDate" in attrib:
            del attrib["endDate"]
        sd, ed = stats.temporal_extent_of_station(code[0], code[1])
        attrib["startDate"] = sd
        if ed is not None:
            attrib["endDate"] = ed

        station.clear()
        station.extend(children)
        station.attrib.update(attrib)

        etree.SubElement(station, "TotalNumberChannels").text = \
            str(stats.channels_for_station(code[0], code[1]))

        # No channels selected for levels 'network' and 'station'
        if level not in ("network", "station"):
            etree.SubElement(station, "SelectedNumberChannels").text = \
                str(len([_i for _i in chans if (_i[0], _i[1]) == code]))
        else:
            etree.SubElement(station, "SelectedNumberChannels").text = "0"

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
