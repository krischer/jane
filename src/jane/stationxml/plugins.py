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
        "azimuth": "float",
        "dip": "float",
        "start_date": "UTCDateTime",
        "end_date": "UTCDateTime",
        "station_creation_date": "UTCDateTime",
        "sample_rate": "float",
        "sensor_type": "str",
        "total_sensitivity": "float",
        "sensitivity_frequency": "float",
        "units_after_sensitivity": "str"
        }

    def index(self, document):
        inv = obspy.read_inventory(document, format="stationxml")
        indices = []
        for network in inv:
            for station in network:
                for channel in station:
                    if channel.response:
                        if channel.response.instrument_sensitivity:
                            _i = channel.response.instrument_sensitivity
                            total_sensitivity = _i.value
                            sensitivity_frequency = _i.frequency
                            units_after_sensitivity = _i.input_units
                        else:
                            total_sensitivity = None
                            sensitivity_frequency = None
                            units_after_sensitivity = None
                    else:
                        total_sensitivity = None
                        sensitivity_frequency = None
                        units_after_sensitivity = None

                    index = {
                        # Information.
                        "network": network.code,
                        "network_name": network.description,
                        "station": station.code,
                        "station_name": station.description if
                        station.description else station.site.name,
                        "location": channel.location_code,
                        "channel": channel.code,

                        # Coordinates and orientation.
                        "latitude": channel.latitude,
                        "longitude": channel.longitude,
                        "elevation_in_m": channel.elevation,
                        "depth_in_m": channel.depth,
                        "dip": channel.dip,
                        "azimuth": channel.azimuth,

                        # Dates.
                        "start_date": str(channel.start_date),
                        "end_date": str(channel.end_date)
                        if channel.end_date is not None else None,
                        # This is strictly speaking not channel level
                        # information but needed to for a fast generation of
                        # the station level fdsnws responses.
                        "station_creation_date": str(station.creation_date)
                        if station.creation_date is not None else None,

                        # Characteristics.
                        "sample_rate": float(channel.sample_rate),
                        "sensor_type": channel.sensor.type
                        if channel.sensor else None,
                        # Some things have to be extracted from the response.
                        "total_sensitivity": total_sensitivity,
                        "sensitivity_frequency": sensitivity_frequency,
                        "units_after_sensitivity": units_after_sensitivity,

                        # Geometry for PostGIS.
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
