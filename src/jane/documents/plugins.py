# -*- coding: utf-8 -*-
import collections
import inspect
import sys

from djangoplugins.point import PluginPoint

from jane import settings


class ValidatorPluginPoint(PluginPoint):
    """
    """
    group_name = "validators"

    def validate(self):
        raise NotImplementedError


class IndexerPluginPoint(PluginPoint):
    """
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


class ConverterPluginPoint(PluginPoint):
    """
    """
    group_name = "converters"

    def convert(self):
        raise NotImplementedError


class OutputConverterPluginPoint(PluginPoint):
    """
    """
    group_name = "output_converters"

    def convert(self):
        raise NotImplementedError


class InputConverterPluginPoint(PluginPoint):
    """
    """
    group_name = "input_converters"

    def convert(self):
        raise NotImplementedError


def initialize_plugins():
    """
    Initializes all found plugins.

    Plug-ins are grouped via their case insensitive 'name' attribute.
    """
    # Import in here to avoid circular imports.
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
        for plugin in obj.get_plugins():
            plugins[plugin.name.lower()][obj.group_name].append(plugin)

    # Convert to dict of dicts to ease further use.
    plugins = {key: dict(value) for key, value in plugins.items()}

    for plugin_name, contents in plugins.items():
        # Create the resource type if it does not yet exist.
        resource_type = models.ResourceType.objects.get_or_create(
            name=plugin_name)[0]
        if "indexer" in contents:
            resource_type.indexer = contents["indexer"][0].get_model()
        if "validators" in contents:
            resource_type.validators = [_i.get_model() for _i in contents[
                "validators"]]
        if "converters" in contents:
            resource_type.converters = [_i.get_model() for _i in contents[
                "converters"]]
        resource_type.save()

    if settings.DEBUG:
        import pprint
        print("Registered Plugins:")
        pprint.pprint(plugins)
