# -*- coding: utf-8 -*-

import io

from django.core.cache import cache
from django.contrib.gis.geos.collections import GeometryCollection
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver

from jane.documents import models


@receiver(pre_save, sender=models.DocumentRevision)
def validate_document(sender, instance, **kwargs):  # @UnusedVariable
    """
    Validate document before saving using validators of specified document type
    """
    plugins = instance.document.document_type.validators.all()
    with io.BytesIO(bytes(instance.data)) as data:
        for plugin in plugins:
            data.seek(0, 0)
            # raise if not valid
            if not plugin.get_plugin().validate(data):
                raise Exception


@receiver(post_save, sender=models.DocumentRevision)
def index_document(sender, instance, created, **kwargs):  # @UnusedVariable
    """
    Index data
    """
    # delete all existing indexed data
    instance.indices.all().delete()
    plugins = instance.document.document_type.indexers.all()
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
                obj = models.DocumentRevisionIndex(revision=instance,
                                                   json=index)
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
                        models.DocumentRevisionIndexAttachment(
                            index=obj, category=key,
                            content_type=value['content-type'],
                            data=data).save()
    # invalidate cache
    cache.delete('record_list_json')
