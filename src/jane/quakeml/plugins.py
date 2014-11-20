# -*- coding: utf-8 -*-
from obspy.core.quakeml import _validate as validate_quakeml

from django.contrib.gis.geos.point import Point
from obspy.core.event import readEvents

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
            "quakeml_id": {"type": "str"},
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "depth_in_m": {"type": "float"},
            "origin_time": {"type": "datetime"},
            "magnitude": {"type": "float"},
            "magnitude_type": {"type": "str"},
            "agency": {"type": "str"},
            "author": {"type": "str"},
            "public": {"type": "bool"},
            "evaluation_mode": {"type": "str"},
            "event_type": {"type": "str"}
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

            # Parse attributes in the baynet namespace.
            if hasattr(event, "extra"):
                if "public" in event.extra:
                    public = event.extra["public"]["value"]
                    if public.lower() in ["false", "f"]:
                        public = False
                    elif public.lower() in ["true", "t"]:
                        public = True
                    else:
                        raise NotImplementedError
                else:
                    public = None
                if "evaluationMode" in event.extra:
                    evaluationMode = event.extra["evaluationMode"]["value"]
                else:
                    evaluationMode = None
            else:
                public = None
                evaluationMode = None

            indices.append({
                "quakeml_id": str(event.resource_id),
                "latitude": org.latitude if org else None,
                "longitude": org.longitude if org else None,
                "depth_in_m": org.depth if org else None,
                "origin_time": str(org.time) if org else None,
                "magnitude": mag.mag if mag else None,
                "magnitude_type": mag.magnitude_type if mag else None,
                "agency": \
                    event.creation_info and event.creation_info.agency_id,
                "author": event.creation_info and event.creation_info.author,
                "public": public,
                "evaluation_mode": evaluationMode,
                "event_type": event.event_type,
                "geometry":
                    [Point(org.longitude, org.latitude)] if org else None,
            })

        return indices
