# -*- coding: utf-8 -*-

import io

from django.core.cache import cache
from django.contrib.gis.geos.collections import GeometryCollection
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver

from jane.documents import models


@receiver(pre_save, sender=models.Document)
def validate_document(sender, instance, **kwargs):  # @UnusedVariable
    """
    Validate document before saving using validators of specified document type
    """
    plugins = instance.document_type.validators.all()
    if not plugins:
        raise Exception("At least one ValidatorPlugin must be defined for "
                        "document type '%s'." %
                        instance.document_type.name)
    with io.BytesIO(bytes(instance.data)) as data:
        for plugin in plugins:
            data.seek(0, 0)
            # raise if not valid
            if not plugin.get_plugin().validate(data):
                raise Exception


@receiver(pre_save, sender=models.Document)
def set_content_type(sender, instance, **kwargs):  # @UnusedVariable
    # One of the validators must contain a content-type of the data.
    validators = instance.document_type.validators.all()
    content_types = []
    for validator in validators:
        plugin = validator.get_plugin()
        if hasattr(plugin, "content_type"):
            content_types.append(plugin.content_type)
    content_types = set(content_types)
    if not content_types:
        raise Exception("At least one of the validators must contains a "
                        "content type.")
    if len(content_types) != 1:
        raise Exception("More then one content type defined for the document "
                        "types validators")
    content_type = content_types.pop()
    instance.content_type = content_type


@receiver(post_save, sender=models.Document)
def index_document(sender, instance, created, **kwargs):  # @UnusedVariable
    """
    Index data
    """
    # delete all existing indexed data
    instance.indices.all().delete()
    plugins = instance.document_type.indexers.all()
    for plugin in plugins:
        indexer = plugin.get_plugin()
        # index data
        with io.BytesIO(bytes(instance.data)) as data:
            indices = indexer.index(data)
            for index in indices:
                # attachments
                attachments = index.get('attachments')
                try:
                    del index['attachments']
                except:
                    pass
                # geometry
                geometry = index.get('geometry')
                try:
                    del index['geometry']
                except:
                    pass
                # add index
                obj = models.DocumentIndex(document=instance, json=index)
                if geometry:
                    obj.geometry = GeometryCollection(geometry)
                obj.save()
                # add attachments
                if attachments:
                    for key, value in attachments.items():
                        data = value['data']
                        if hasattr(data, 'seek'):
                            data.seek(0)
                            data = data.read()
                        models.DocumentIndexAttachment(
                            index=obj, category=key,
                            content_type=value['content-type'],
                            data=data).save()
    # invalidate cache
    cache.delete('record_list_json')
