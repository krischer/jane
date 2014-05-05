# -*- coding: utf-8 -*-

import io

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
    instance.indexed_values.all().delete()
    # index data
    with io.BytesIO(bytes(instance.data)) as data:
        indices = indexer.index(data)
        for index in indices:
            attachments = index.get('attachments')
            try:
                del index['attachments']
            except:
                pass
            # add indices
            obj = models.IndexedValue(document=instance, json=index)
            obj.save()
            # add attachments
            for key, value in attachments.items():
                try:
                    data = value['data'].seek(0)
                    data = data.read()
                except:
                    data = value['data']
                models.IndexedValueAttachment(indexed_value=obj, category=key,
                    content_type=value['content_type'], data=data).save()
