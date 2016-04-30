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
        except:
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

    def filter_queryset_user_has_permission(self, queryset, model_type):
        # If the user has the permission, everything is fine and the
        # original queryset can be returned.
        return queryset

    def filter_queryset_user_does_not_have_permission(self, queryset,
                                                      model_type):
        # model_type can be document or document index.
        if model_type == "document":
            # XXX: Find a good way to do this.
            pass
        elif model_type == "index":
            # Modify the queryset to only contain indices that are public.
            # Events that have null for public are considered to be private
            # and will not be shown here.
            queryset = queryset.model.objects.get_filtered_queryset(
                document_type="quakeml", queryset=queryset, public=True)
        else:
            raise NotImplementedError()
        return queryset


def _site_magnitude_threshold_retrieve_permission(
        class_name, magnitude_threshold, site=None):
    """
    Class factory that returns a quakeml retrieve permission based on a
    magnitude threshold, optionally only working on a specific site.
    If multiple of these restrictions are defined, all of them apply separately
    and the user must have all of them set, down to the lowest threshold
    restriction that is supposed to apply.
    """
    class _SiteMagnitudeThresholdRetrievePermissionPlugin(
            RetrievePermissionPluginPoint):
        """
        If user does not have this permission, any events below given magnitude
        threshold are filtered out (optionally only for a specific site).
        """
        name = 'quakeml'
        title = 'Can See Magnitude <{} Events {}Permission'.format(
            magnitude_threshold, site and "At site='{}' ".format(site) or "")

        # Permission codename and name according to Django's nomenclature.
        # XXX no idea if dots are allowed in codename, so replace them
        permission_codename = 'can_see_mag_lessthan_{}_site_{}_events'.format(
            magnitude_threshold, site or "any").replace(".", "_")
        permission_name = 'Can See Magnitude <{} Events{}'.format(
            magnitude_threshold, site and " At site='{}'".format(site) or "")

        def filter_queryset_user_has_permission(self, queryset, model_type):
            # If the user has the permission: don't restrict queryset.
            return queryset

        def filter_queryset_user_does_not_have_permission(self, queryset,
                                                          model_type):
            # model_type can be document or document index.
            if model_type == "document":
                # XXX: Find a good way to do this.
                raise NotImplementedError()
            elif model_type == "index":
                # Modify the queryset to only contain indices that are above
                # given magnitude threshold.
                # XXX check what happens with events that have null for
                # XXX magnitude..
                kwargs = {}
                # if no site is specified, just do a normal filter by magnitude
                # threshold
                if site is None:
                    kwargs["min_magnitude"] = magnitude_threshold
                    negate = False
                # if site is specified, we need to search for events matching
                # both criteria and then invert the resulting queryset
                else:
                    kwargs['site'] = site
                    kwargs["max_magnitude"] = magnitude_threshold - 0.01
                    negate = True
                queryset = queryset.model.objects.get_filtered_queryset(
                    document_type="quakeml", queryset=queryset, negate=negate,
                    **kwargs)
            else:
                raise NotImplementedError()
            return queryset

    new_class = _SiteMagnitudeThresholdRetrievePermissionPlugin
    # Set the class type name.
    setattr(new_class, "__name__", class_name)
    return new_class


# Retrieve permissions for small events, if users don't have these permissions
# small events are not accessible to them
MagnitudeLessThan1RetrievePermissionPlugin = \
    _site_magnitude_threshold_retrieve_permission(
        "MagnitudeLessThan1RetrievePermissionPlugin", magnitude_threshold=1.0)
MagnitudeLessThan2RetrievePermissionPlugin = \
    _site_magnitude_threshold_retrieve_permission(
        "MagnitudeLessThan2RetrievePermissionPlugin", magnitude_threshold=2.0)

# Retrieve permissions for small events attributed to a specific site (e.g. a
# specific deep geothermal project), if users don't have these permissions
# small events that are attributed to that site are not accessible to them
UnterhachingLessThan1RetrievePermissionPlugin = \
    _site_magnitude_threshold_retrieve_permission(
        "UnterhachingLessThan1RetrievePermissionPlugin",
        magnitude_threshold=1.0, site="geothermie_unterhaching")
UnterhachingLessThan2RetrievePermissionPlugin = \
    _site_magnitude_threshold_retrieve_permission(
        "UnterhachingLessThan2RetrievePermissionPlugin",
        magnitude_threshold=2.0, site="geothermie_unterhaching")


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
        "site": "str",
    }

    def index(self, document):
        """
        The method that actually performs the indexing.

        :param document: The document as a memory file.
        """
        from django.contrib.gis.geos.point import Point  # NOQA
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
                    evaluationMode = None
            else:
                public = True
            if "evaluationMode" in extra:
                evaluation_mode = extra["evaluationMode"]["value"]
            else:
                evaluation_mode = None
            if "site" in extra:
                site = extra["site"]["value"]
            else:
                site = None

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
                # The special key geometry can be used to store geographic
                # information about the indexes geometry. Useful for very
                # fast queries using PostGIS.
                "geometry":
                    [Point(org.longitude, org.latitude)] if org else None,
                "site": site,
            })

        return indices
