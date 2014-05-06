# -*- coding: utf-8 -*-
from jane.documents.plugins import ValidatorPluginPoint, IndexerPluginPoint

import io
import obspy
from obspy.station.stationxml import validate_StationXML


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

    @property
    def meta(self):
        """
        types: string, date, datetime, bool, int, float
        """
        return {'num_traces': {'type': 'string',
                               'minimum_allowed': True,
                               'wildcard_allowed': True}
        }

    def index(self, document):
        inv = obspy.read_inventory(document, format="stationxml")
        indices = []
        for network in inv:
            for station in network:
                for channel in station:
                    # Plot response.
                    plot = io.BytesIO()
                    channel.plot(min_freq=1E-3, outfile=plot)
                    plot.seek(0)

                    indices.append({
                        "network": network.code,
                        "station": station.code,
                        "location": channel.location_code,
                        "channel": channel.code,
                        "latitude": channel.latitude,
                        "longitude": channel.longitude,
                        "elevation_in_m": channel.elevation,
                        "depth_in_m": channel.depth,
                        "start_date": str(channel.start_date),
                        "end_date": str(channel.end_date),
                        "attachments": {
                            "response": {"content-type": "image/png",
                                         "data": plot.read()}
                        }
                    })

        return indices
