# -*- coding: utf-8 -*-

import hashlib
import io

from django.core.cache import cache
from django.contrib.gis.geos.collections import GeometryCollection
from django.db.models.signals import pre_save, post_save
from django.dispatch.dispatcher import receiver


from jane.documents import models, JaneDocumentsValidationException


@receiver(pre_save, sender=models.Document)
def validate_document(sender, instance, **kwargs):
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
                raise JaneDocumentsValidationException(
                    "Not a valid document of type %s." %
                    instance.document_type.name)


@receiver(pre_save, sender=models.Document)
def set_document_metadata(sender, instance, **kwargs):
    # If not set, use the default content type for that particular document
    # type.
    if not instance.content_type:
        instance.content_type = \
            instance.document_type.definition.get_plugin().default_content_type

    # Set the filesize and calculate the hash. No need to check the hash as
    # the database constraints will enforce its uniqueness.
    instance.filesize = len(instance.data)
    instance.sha1 = hashlib.sha1(instance.data).hexdigest()


@receiver(post_save, sender=models.Document)
def index_document(sender, instance, created, **kwargs):  # @UnusedVariable
    """
    Index data
    """
    # delete all existing indexed data
    instance.indices.all().delete()
    indexer = instance.document_type.indexer.get_plugin()
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
                        data=data,
                        created_by=instance.created_by,
                        modified_by=instance.modified_by,
                    ).save()
    # invalidate cache
    cache.delete('record_list_json')
