# -*- coding: utf-8 -*-
import io

from django.contrib.gis.geos.point import Point

import matplotlib
# Use anti-grain geometry interface which does not require an open display.
matplotlib.use('agg')
import matplotlib.pylab as plt  # noqa

from obspy.station.stationxml import validate_StationXML  # noqa
import obspy  # noqa

from jane.documents.plugins import (ValidatorPluginPoint, IndexerPluginPoint,
                                    DocumentPluginPoint)  # noqa


class StationXMLPlugin(DocumentPluginPoint):
    name = 'stationxml'
    title = "StationXML Plugin for Jane's Document Database"
    default_content_type = 'text/xml'


class StationValidatorPlugin(ValidatorPluginPoint):
    name = 'stationxml'
    title = 'StationXML XMLSchema Validator'

    def validate(self, document):
        is_stationxml, error = validate_StationXML(document)
        if not is_stationxml:
            raise ValueError(error)
        return True


class StationIndexerPlugin(IndexerPluginPoint):
    name = 'stationxml'
    title = 'StationXML Indexer'

    meta = {
        "network": "str",
        "station": "str",
        "location": "str",
        "channel": "str",
        "latitude": "float",
        "longitude": "float",
        "elevation_in_m": "float",
        "depth_in_m": "float",
        "start_date": "UTCDateTime",
        "end_date": "UTCDateTime",
        "sample_rate": "float",
        "sensor_type": "str"
        }

    def index(self, document):
        inv = obspy.read_inventory(document, format="stationxml")
        indices = []
        for network in inv:
            for station in network:
                for channel in station:
                    index = {
                        "network": network.code,
                        "network_name": network.description,
                        "station": station.code,
                        "station_name": station.description if
                        station.description else station.site.name,
                        "location": channel.location_code,
                        "channel": channel.code,
                        "latitude": channel.latitude,
                        "longitude": channel.longitude,
                        "elevation_in_m": channel.elevation,
                        "depth_in_m": channel.depth,
                        "start_date": str(channel.start_date),
                        "sample_rate": float(channel.sample_rate),
                        "sensor_type": channel.sensor.type
                        if channel.sensor else None,
                        "end_date": str(channel.end_date)
                        if channel.end_date else None,
                        "geometry": [Point(channel.longitude,
                                           channel.latitude)],
                    }

                    try:
                        plt.close()
                    except:
                        pass

                    # Sometimes fails. Wrap in try/except.
                    try:
                        # Plot response.
                        with io.BytesIO() as plot:
                            channel.plot(min_freq=1E-3, outfile=plot)
                            plot.seek(0)
                            index["attachments"] = {
                                "response": {"content-type": "image/png",
                                             "data": plot.read()}}
                    except (AttributeError, TypeError):
                        pass

                    indices.append(index)

        return indices
