# -*- coding: utf-8 -*-
import collections
import inspect
import sys

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

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


class RetrievePermissionPluginPoint(PluginPoint):
    """
    Plugin point for custom permission upon retrieving documents and indices.
    """
    group_name = "retrieve_permissions"

    def filter_queryset_user_has_permission(self, queryset, model_type):
        raise NotImplementedError

    def filter_queryset_user_does_not_have_permission(self, queryset,
                                                      model_type):
        raise NotImplementedError


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

    # Set optional arguments as they might not exist for every plugin.
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
        # Validators are optional.
        if "validators" in contents:
            validators = [_i.get_model() for _i in contents["validators"]]
        else:
            validators = []
        # Retreive permissions are also optional.
        if "retrieve_permissions" in contents:
            retrieve_permissions = [
                _i.get_model() for _i in contents["retrieve_permissions"]]
        else:
            retrieve_permissions = []
        print(retrieve_permissions)

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

    # Permissions.
    permissions = []
    for plugin_name in plugins.keys():
        # Two default permissions for every plugin: Can upload documents and
        # attachments.
        permissions.append(
            {"codename": "can_upload_%s" % plugin_name,
             "name": "Can Upload %s Documents" % plugin_name.capitalize()})
        permissions.append(
            {"codename": "can_upload_%s_attachments" % plugin_name,
             "name": "Can Upload Attachments for %s Indices" %
                     plugin_name.capitalize()})

    content_type = ContentType.objects.get_for_model(models.DocumentType)
    for perm in permissions:
        try:
            p = Permission.objects.get(codename=perm["codename"])
            p.name = perm["name"]
            p.content_type = content_type
        except Permission.DoesNotExist:
            p = Permission.objects.create(
                codename=perm["codename"],
                name=perm["name"],
                content_type=content_type)
        p.save()
