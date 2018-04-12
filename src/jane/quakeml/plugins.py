# -*- coding: utf-8 -*-
"""
QuakeML Plug-in for Jane's Document Database.

This file also serves as a template/tutorial to create new plug-ins and is
thus extensively commented.
"""
# In the interest of quick import/startup times, please try to import within
# the functions and not at the file level.
from jane.documents.plugins import (ValidatorPluginPoint, IndexerPluginPoint,
                                    DocumentPluginPoint,
                                    RetrievePermissionPluginPoint)


class QuakeMLPlugin(DocumentPluginPoint):
    """
    Each document type for Jane's Document Database must have a
    DocumentPluginPoint with some basic meta information.
    """
    # Each plug-in for a certain document type must share the same name.
    # That's how the plug-ins are grouped per document type.
    name = 'quakeml'
    # The title is only for this particular plug-in point and is used in
    # places where a pretty name is desired.
    title = "QuakeML Plugin for Jane's Document Database"

    # Each document must have a content type. If not specified during the
    # initial upload of the document, this value will be used.
    default_content_type = 'text/xml'


class QuakeMLValidatorPlugin(ValidatorPluginPoint):
    """
    Any number of validators can be defined for each document type.

    Each validator must have a validate() method that returns True or False
    depending on weather or not the particular validation has passed or not.
    Only documents that pass all validations can be stored in the database.
    """
    name = 'quakeml'
    title = 'QuakeML XMLSchema Validator'

    def validate(self, document):
        from obspy.io.quakeml.core import _validate as validate_quakeml  # NOQA
        try:
            is_valid = validate_quakeml(document)
        except Exception:
            is_valid = False
        return is_valid


class CanSeePrivateEventsRetrievePermissionPlugin(
        RetrievePermissionPluginPoint):
    """
    Custom permissions are possible but optional and fairly complex.
    """
    name = 'quakeml'
    title = 'Can See Private Events Permission'

    # Permission codename and name according to Django's nomenclature.
    permission_codename = 'can_see_private_events'
    permission_name = 'Can See Private Events'

    def filter_queryset_user_has_permission(self, queryset, model_type, user):
        # If the user has the permission, everything is fine and the
        # original queryset can be returned.
        return queryset

    def filter_queryset_user_does_not_have_permission(self, queryset,
                                                      model_type, user):
        # model_type can be document or document index.
        if model_type == "document":
            # XXX: Find a good way to do this.
            pass
        elif model_type == "index":
            # Modify the queryset to only contain indices that are public.
            # Events that have null for public are considered to be private
            # and will not be shown here.
            queryset = queryset.filter(json__public=True)
        else:
            raise NotImplementedError()
        return queryset


class QuakeMLIndexerPlugin(IndexerPluginPoint):
    """
    Each document type can have one indexer.

    Upon uploading, the indexer will parse the uploaded document and extract
    information from it as a list of dictionaries. Each dictionary is the
    index for one particular logical part in the document. A document may
    have one or more indices. In this case here one index will be created
    and stored per event in the QuakeML file.

    Each index will be stored as a JSON file in the database and can be
    searched upon.
    """
    name = 'quakeml'
    title = 'QuakeML Indexer'

    # The meta property defines what keys from the indices can be searched
    # on. For this to work it has to know the type for each key. Possible
    # values for the type are "str", "int", "float", "bool", and "UTCDateTime".
    meta = {
        "quakeml_id": "str",
        "latitude": "float",
        "longitude": "float",
        "depth_in_m": "float",
        "origin_time": "UTCDateTime",
        "magnitude": "float",
        "magnitude_type": "str",
        "agency": "str",
        "author": "str",
        "public": "bool",
        "evaluation_mode": "str",
        "event_type": "str",
        "has_focal_mechanism": "bool",
        "has_moment_tensor": "bool",
        "horizontal_uncertainty_max": "float",
        "horizontal_uncertainty_min": "float",
        "horizontal_uncertainty_max_azimuth": "float",
    }

    def index(self, document):
        """
        The method that actually performs the indexing.

        :param document: The document as a memory file.
        """
        from django.contrib.gis.geos import (
            Point, LineString, MultiLineString)
        from obspy import read_events

        # Collect all indices in a list. Each index has to be a dictionary.
        indices = []

        inv = read_events(document, format="quakeml")

        for event in inv:
            if event.origins:
                org = event.preferred_origin() or event.origins[0]
            else:
                org = None

            if event.magnitudes:
                mag = event.preferred_magnitude() or event.magnitudes[0]
            else:
                mag = None

            has_focal_mechanism = False
            has_moment_tensor = False
            if event.focal_mechanisms:
                has_focal_mechanism = True
                if any(mt for mt in event.focal_mechanisms):
                    has_moment_tensor = True

            # Parse attributes in the baynet namespace.
            # The public attribute defaults to True, it can only be set to
            # False by utilizing the baynet namespace as of now.
            extra = event.get("extra", {})
            if "public" in extra:
                public = extra["public"]["value"]
                if public.lower() in ["false", "f"]:
                    public = False
                elif public.lower() in ["true", "t"]:
                    public = True
                else:
                    public = None
            else:
                public = True
            if "evaluationMode" in extra:
                evaluation_mode = extra["evaluationMode"]["value"]
            else:
                evaluation_mode = None
            # parse horizontal uncertainties
            if org and org.origin_uncertainty:
                org_unc = org.origin_uncertainty
                if org_unc.preferred_description == 'horizontal uncertainty':
                    horizontal_uncertainty_max = org_unc.horizontal_uncertainty
                    horizontal_uncertainty_min = org_unc.horizontal_uncertainty
                    horizontal_uncertainty_max_azimuth = 0
                elif org_unc.preferred_description == 'uncertainty ellipse':
                    horizontal_uncertainty_max = \
                        org_unc.max_horizontal_uncertainty
                    horizontal_uncertainty_min = \
                        org_unc.min_horizontal_uncertainty
                    horizontal_uncertainty_max_azimuth = \
                        org_unc.azimuth_max_horizontal_uncertainty
                else:
                    horizontal_uncertainty_max = None
                    horizontal_uncertainty_min = None
                    horizontal_uncertainty_max_azimuth = None
            else:
                horizontal_uncertainty_max = None
                horizontal_uncertainty_min = None
                horizontal_uncertainty_max_azimuth = None

            geometry = None
            if org:
                geometry = [Point(org.longitude, org.latitude)]
                if all(value is not None for value in (
                        horizontal_uncertainty_max, horizontal_uncertainty_min,
                        horizontal_uncertainty_max_azimuth)):
                    import geopy
                    import geopy.distance
                    start = geopy.Point(latitude=org.latitude,
                                        longitude=org.longitude)
                    lines = []
                    for distance, azimuth in (
                            (horizontal_uncertainty_max,
                             horizontal_uncertainty_max_azimuth),
                            (horizontal_uncertainty_min,
                             horizontal_uncertainty_max_azimuth + 90)):
                        azimuth = azimuth % 180
                        distance = geopy.distance.VincentyDistance(
                            kilometers=distance / 1e3)
                        end1 = distance.destination(
                            point=start, bearing=azimuth)
                        end2 = distance.destination(
                            point=start, bearing=azimuth + 180)
                        line = LineString((end1.longitude, end1.latitude),
                                          (org.longitude, org.latitude),
                                          (end2.longitude, end2.latitude))
                        lines.append(line)
                    geometry.append(MultiLineString(lines))
                else:
                    geometry.append(MultiLineString([]))

            indices.append({
                "quakeml_id": str(event.resource_id),
                "latitude": org.latitude if org else None,
                "longitude": org.longitude if org else None,
                "depth_in_m": org.depth if org else None,
                "origin_time": str(org.time) if org else None,
                "magnitude": mag.mag if mag else None,
                "magnitude_type": mag.magnitude_type if mag else None,
                "agency":
                event.creation_info and event.creation_info.agency_id or None,
                "author":
                event.creation_info and event.creation_info.author or None,
                "public": public,
                "evaluation_mode": evaluation_mode,
                "event_type": event.event_type,
                "has_focal_mechanism": has_focal_mechanism,
                "has_moment_tensor": has_moment_tensor,
                # The special key geometry can be used to store geographic
                # information about the indexes geometry. Useful for very
                # fast queries using PostGIS.
                "geometry": geometry,
                "horizontal_uncertainty_max": horizontal_uncertainty_max,
                "horizontal_uncertainty_min": horizontal_uncertainty_min,
                "horizontal_uncertainty_max_azimuth":
                    horizontal_uncertainty_max_azimuth,
            })

        return indices
