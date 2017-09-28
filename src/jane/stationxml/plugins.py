# -*- coding: utf-8 -*-
import io

from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.geos.point import Point

import matplotlib
# Use anti-grain geometry interface which does not require an open display.
matplotlib.use('agg')
import matplotlib.pylab as plt  # noqa

from obspy.io.stationxml.core import validate_stationxml  # noqa
import obspy  # noqa

from jane.documents.plugins import (
    ValidatorPluginPoint, IndexerPluginPoint, DocumentPluginPoint,
    RetrievePermissionPluginPoint)  # noqa
from jane.waveforms.models import Restriction  # noqa


class StationXMLPlugin(DocumentPluginPoint):
    name = 'stationxml'
    title = "StationXML Plugin for Jane's Document Database"
    default_content_type = 'text/xml'


class StationValidatorPlugin(ValidatorPluginPoint):
    name = 'stationxml'
    title = 'StationXML XMLSchema Validator'

    def validate(self, document):
        is_stationxml, error = validate_stationxml(document)
        if not is_stationxml:
            raise ValueError(error)
        return True


class CanSeeAllStations(RetrievePermissionPluginPoint):
    """
    If a user does not have this permission, the waveform restrictions will
    also apply to the documents.
    """
    name = 'stationxml'
    title = 'Can See All Stations'

    # Permission codename and name according to Django's nomenclature.
    permission_codename = 'can_see_all_stations'
    permission_name = 'Can See All Stations'

    def filter_queryset_user_has_permission(self, queryset, model_type, user):
        # If the user has the permission, everything is fine and the
        # original queryset can be returned.
        return queryset

    def filter_queryset_user_does_not_have_permission(self, queryset,
                                                      model_type, user):
        if not user or isinstance(user, AnonymousUser):
            restrictions = Restriction.objects.all()
        else:
            restrictions = Restriction.objects.exclude(users=user)

        # model_type can be document or document index.
        if model_type == "document":
            # XXX: Find a good way to do this.
            pass
        elif model_type == "index":
            for restriction in restrictions:
                kwargs = {}
                # XXX in principle this could be handled simply by using a
                # regex field lookup on the json field below, but in Django <
                # 1.11 there's a bug so the regex lookup doesn't work, see
                # django/django#6929
                if restriction.network == '*' and restriction.station == '*':
                    # if both network and station are '*' then all stations are
                    # restricted
                    return queryset.none()
                elif restriction.network == '*':
                    kwargs['json__station'] = restriction.station
                elif restriction.station == '*':
                    kwargs['json__network'] = restriction.network
                else:
                    kwargs['json__network'] = restriction.network
                    kwargs['json__station'] = restriction.station
                queryset = queryset.exclude(**kwargs)
        else:
            raise NotImplementedError()
        return queryset


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
                    except Exception:
                        pass
                    finally:
                        try:
                            plt.close()
                        except:
                            pass

                    indices.append(index)

        return indices
