# -*- coding: utf-8 -*-

import csv
import io

from lxml import etree
from obspy import UTCDateTime
from obspy.geodetics import FlinnEngdahl

from jane.documents.models import DocumentIndex


FG = FlinnEngdahl()


def query_event(fh, nodata, orderby, format, starttime=None, endtime=None,
                minlatitude=None, maxlatitude=None, minlongitude=None,
                maxlongitude=None, mindepth_in_km=None, maxdepth_in_km=None,
                minmagnitude=None, maxmagnitude=None, latitude=None,
                longitude=None, minradius=None, maxradius=None,
                contributor=None):
    """
    Process query and generate a combined QuakeML or event text file.
    Parameters are interpreted as in the FDSNWS definition. Results are
    written to fh. A returned numeric status code is interpreted as in the
    FDSNWS definition.
    """
    kwargs = {}

    if starttime is not None:
        kwargs["min_origin_time"] = UTCDateTime(starttime)
    if endtime is not None:
        kwargs["max_origin_time"] = UTCDateTime(endtime)

    # Spatial constraints.
    if minlatitude is not None:
        kwargs["min_latitude"] = minlatitude
    if maxlatitude is not None:
        kwargs["max_latitude"] = maxlatitude
    if minlongitude is not None:
        kwargs["min_longitude"] = minlongitude
    if maxlongitude is not None:
        kwargs["max_longitude"] = maxlongitude
    if mindepth_in_km is not None:
        kwargs["min_depth_in_m"] = mindepth_in_km * 1000
    if maxdepth_in_km is not None:
        kwargs["max_depth_in_m"] = maxdepth_in_km * 1000
    if minmagnitude is not None:
        kwargs["min_magnitude"] = minmagnitude
    if maxmagnitude is not None:
        kwargs["max_magnitude"] = minmagnitude

    # Jane maps the contributor to the agency.
    if contributor is not None:
        kwargs["agency"] = contributor

    query = DocumentIndex.objects.get_filtered_queryset(
        document_type="quakeml", **kwargs)

    # Apply the ordering on the JSON fields.
    # XXX: Can be replaced in Django 1.9 with the native JSON fields. Maybe
    # there is some other nice way in the meantime?
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

    # Radial queries.
    if latitude is not None:
        query = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", queryset=query,
            central_latitude=latitude, central_longitude=longitude,
            min_radius=minradius, max_radius=maxradius)

    results = query.all()
    if not results:
        return nodata

    if format == "xml":
        nsmap = {None: "http://quakeml.org/xmlns/bed/1.2",
                 "ns0": "http://quakeml.org/xmlns/quakeml/1.2"}
        root_el = etree.Element('{%s}quakeml' % nsmap["ns0"],
                                nsmap=nsmap)
        catalog_el = etree.Element('eventParameters',
                                   attrib={'publicID': "hmmm"})
        root_el.append(catalog_el)
        # Inverse is true for the stations.

        # Now things get a bit more interesting and this might actually require
        # a different approach to be fast enough.
        for result in results:
            quakeml_id = result.json["quakeml_id"]
            data = io.BytesIO(result.document.data)
            event = get_event_node(data, quakeml_id)
            if event is None:
                continue
            catalog_el.append(event)

        etree.ElementTree(root_el).write(fh, pretty_print=True,
                                         encoding="utf-8",
                                         xml_declaration=True)
    elif format == "text":
        header = ["EventID", "Time", "Latitude", "Longitude", "Depth/km",
                  "Author", "Catalog", "Contributor", "ContributorID",
                  "MagType", "Magnitude", "MagAuthor", "EventLocationName"]
        json_keys = ["quakeml_id", "origin_time", "latitude", "longitude",
                     "depth_in_m", None, None, None, None, "magnitude_type",
                     "magnitude", None]

        # Must be written to text buffer.
        with io.String(newline='') as csvfile:
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
            csvfile.seek(0, 0)
            # Encode to a byte buffer.
            fh.write(csvfile.read().encode())
    else:
        raise NotImplementedError
    return 200


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
