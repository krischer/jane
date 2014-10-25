# -*- coding: utf-8 -*-

import io

from django.contrib.gis.geos.collections import GeometryCollection
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver

from jane.documents import models


@receiver(pre_save, sender=models.Document)
def validate_document(sender, instance, **kwargs):  # @UnusedVariable
    """
    Validate document before saving using validators of specified resource type
    """
    plugins = instance.resource.resource_type.validators.all()
    with io.BytesIO(bytes(instance.data)) as data:
        for plugin in plugins:
            data.seek(0, 0)
            # raise if not valid
            if not plugin.get_plugin().validate(data):
                raise Exception


@receiver(post_save, sender=models.Document)
def index_document(sender, instance, created, **kwargs):  # @UnusedVariable
    """
    Index data
    """
    indexer = instance.resource.resource_type.indexer.get_plugin()
    # delete all existing indexed data
    instance.records.all().delete()
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
            # add record
            obj = models.Record(document=instance, json=index)
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
                    models.Attachment(record=obj, category=key,
                        content_type=value['content-type'], data=data).save()
