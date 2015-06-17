# -*- coding: utf-8 -*-
import collections
import inspect
import sys

from djangoplugins.point import PluginPoint

from jane.exceptions import JaneException


class JaneDocumentsPluginException(JaneException):
    pass


class DocumentPluginPoint(PluginPoint):
    """
    Each document type must specify one of these which is used to specify
    per-document-type meta information.
    """
    group_name = "definition"


class ValidatorPluginPoint(PluginPoint):
    """
    Plugin point for the validators of a certain plugin.
    """
    group_name = "validators"

    def validate(self):
        raise NotImplementedError


class IndexerPluginPoint(PluginPoint):
    """
    Plugin point for the indexer of a certain plugin.
    """
    group_name = "indexer"

    def index(self):
        """
        """
        raise NotImplementedError

    @property
    def meta(self):
        """
        """
        raise NotImplementedError

    @property
    def keys(self):
        return self.meta.keys()


def initialize_plugins():
    """
    Initializes all found plugins.

    Plug-ins are grouped via their case insensitive 'name' attribute.
    """
    # Import in here to avoid importing models when setup for this app is
    # called.
    from jane.documents import models

    # Get all subclasses of PluginPoint defined in this module.
    current_module = sys.modules[__name__]
    plugin_points = {}
    for name, obj in inspect.getmembers(current_module):
        if not inspect.isclass(obj) or not issubclass(obj, PluginPoint) or \
                obj == PluginPoint:
            continue
        plugin_points[name] = obj

    # Get all registered plugins.
    plugins = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for name, obj in plugin_points.items():
        # Might fail on the migrate run. obj.plugins will be empty in this
        # case.
        try:
            [_i for _i in obj.get_plugins()]
        except:
            pass

        for plugin in obj.plugins:
            plugins[plugin.name.lower()][obj.group_name].append(plugin)

    # Convert to dict of dicts to ease further use.
    plugins = {key: dict(value) for key, value in plugins.items()}

    # Make sure the definition is available for each plugin-group. Otherwise
    # raise an error.
    for plugin_name, contents in plugins.items():
        # Furthermore only one definition and only one indexer is allowed.
        if "definition" not in contents or len(contents["definition"]) != 1:
            raise JaneDocumentsPluginException(
                "The '%s' plug-in must have exactly 1 'DocumentPluginPoint' "
                "instance." % plugin_name)
        # Furthermore only one definition and only one indexer is allowed.
        if "indexer" not in contents or len(contents["indexer"]) != 1:
            raise JaneDocumentsPluginException(
                "The '%s' plug-in must have exactly 1 'IndexPluginPoint' "
                "instance." % plugin_name)

    # Create a database entry for every found document type.
    for plugin_name, contents in plugins.items():
        definition = contents["definition"][0].get_model()
        indexer = contents["indexer"][0].get_model()
        validators = [_i.get_model() for _i in contents["validators"]]

        try:
            resource_type = models.DocumentType.objects.get(name=plugin_name)
            resource_type.definition = definition
            resource_type.indexer = indexer
        except models.DocumentType.DoesNotExist:
            resource_type = models.DocumentType(
                name=plugin_name,
                definition=definition,
                indexer=indexer)
            resource_type.save()

        resource_type.validators = validators
        resource_type.save()
