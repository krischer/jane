# -*- coding: utf-8 -*-

from obspy.core.quakeml import _validate as validate_quakeml
import io

from django.contrib.gis.geos.point import Point
from obspy.core.event import readEvents, Catalog

from jane.documents.plugins import ValidatorPluginPoint, IndexerPluginPoint
import matplotlib.pyplot as plt


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
            if event.origins:
                org = event.preferred_origin() or event.origins[0]
            else:
                org = None

            if event.magnitudes:
                mag = event.preferred_magnitude() or event.magnitudes[0]
            else:
                mag = None

            if mag and org:
                plot = io.BytesIO()
                fig = Catalog(events=[event]).plot(format="png", outfile=plot)
                plt.close(fig)
                plot.seek(0)
                plot_data = plot.read()
                plot.close()

            indices.append({
                "latitude": org.latitude if org else None,
                "longitude": org.longitude if org else None,
                "depth_in_m": org.depth if org else None,
                "origin_time": str(org.time) if org else None,
                "magnitude": mag.mag if mag else None,
                "magnitude_type": mag.magnitude_type if mag else None,
                "geometry":
                    [Point(org.longitude, org.latitude)] if org else None,
            })

            if mag and org:
                indices[-1]["attachments"] = {
                    "map": {"content-type": "image/png", "data": plot_data}}

        return indices
