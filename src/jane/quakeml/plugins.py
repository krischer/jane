# -*- coding: utf-8 -*-

import io

import matplotlib.pyplot as plt
from obspy.core.event import readEvents, Catalog
from obspy.core.quakeml import _validate as validate_quakeml

from jane.documents.plugins import ValidatorPluginPoint, IndexerPluginPoint


class QuakeMLValidatorPlugin(ValidatorPluginPoint):
    name = 'quakeml'
    title = 'QuakeML XMLSchema Validator'

    def validate(self, document):
        return validate_quakeml(document)


class QuakeMLIndexerPlugin(IndexerPluginPoint):
    name = 'quakeml'
    title = 'QuakeML Indexer'

    @property
    def meta(self):
        return {
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "depth_in_m": {"type": "float"},
            "origin_time": {"type": "datetime"},
            "magnitude": {"type": "float"},
            "magnitude_type": {"type": "str"}
        }

    def index(self, document):
        indices = []

        inv = readEvents(document, format="quakeml")
        for event in inv:
            org = event.preferred_origin() or event.origins[0]
            mag = event.preferred_magnitude() or event.magnitudes[0]

            plot = io.BytesIO()
            fig = Catalog(events=[event]).plot(format="png", outfile=plot)
            plt.close(fig)
            plot.seek(0)

            indices.append({
                "latitude": org.latitude,
                "longitude": org.longitude,
                "depth_in_m": org.depth,
                "origin_time": str(org.time),
                "magnitude": mag.mag,
                "magnitude_type": mag.magnitude_type,
                "attachments": {
                    "map": {"content-type": "image/png", "data": plot.read()}
                }
            })
            plot.close()
        return indices
