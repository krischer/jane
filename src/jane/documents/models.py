# -*- coding: utf-8 -*-
"""
Models for the document database of Jane.

The hierarchy is fairly simple:

* There are different types of documents stored in the ``DocumentType`` model.
* Each document type can have various documents stored in the ``Document``
  model.
* Each document can have multiple indices, each stored in a
  ``DocumentIndex`` model
* Each index can have multiple attachments, each stored in a
  ``DocumentIndexAttachment`` model.


New document types can be defined by adding new plug-ins.
"""
from django.conf import settings
from django.contrib.gis.db import models
from djangoplugins.fields import ManyPluginField
from jsonfield.fields import JSONField

from jane.documents import plugins


class PostgreSQLJsonField(JSONField):
    """
    Make the JSONField actually use JSON as a datatype.
    """
    def db_type(self, connection):
        return "json"


class DocumentType(models.Model):
    """
    Document category. Will be determined from the registered plugins.
    """
    name = models.SlugField(max_length=20, primary_key=True)
    # Plugins for this document type.
    indexers = ManyPluginField(plugins.IndexerPluginPoint, null=True,
                               blank=True, related_name='indexers')
    validators = ManyPluginField(plugins.ValidatorPluginPoint, null=True,
                                 blank=True, related_name='validators')
    converters = ManyPluginField(plugins.ConverterPluginPoint, null=True,
                                 blank=True, related_name='converters')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'


class Document(models.Model):
    """
    A document of a particular type.
    """
    document_type = models.ForeignKey(DocumentType, related_name='documents')
    # Name must be given.
    name = models.SlugField(max_length=255, db_index=True)
    # Filename is optional and only serves documentary purposes.
    filename = models.CharField(max_length=255, blank=True, null=True)
    # Content type must be given.
    content_type = models.CharField(max_length=255)
    data = models.BinaryField()
    filesize = models.IntegerField()
    sha1 = models.CharField(max_length=40, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    # Editable in the admin interface; maybe someone wants to change it due
    # to some reason.
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                   editable=True,
                                   related_name='documents_created')

    def __str__(self):
        return "Document of type '%s', name: %s" % (self.document_type,
                                                    self.name)

    class Meta:
        ordering = ['pk']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        unique_together = ['document_type', 'name']

    def save(self, *args, **kwargs):
        super(Document, self).save(*args, **kwargs)


class _DocumentIndexManager(models.GeoManager):
    """
    Custom queryset manager for the document indices.
    """
    def get_queryset(self):
        """
        """
        return super(_DocumentIndexManager, self).get_queryset().\
            select_related('attachments').\
            prefetch_related('attachments')


class DocumentIndex(models.Model):
    """
    Indexed values for a specific document.
    """
    document = models.ForeignKey(Document, related_name='indices')
    json = PostgreSQLJsonField(verbose_name="JSON")
    geometry = models.GeometryCollectionField(blank=True, null=True,
                                              geography=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    objects = _DocumentIndexManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Index'
        verbose_name_plural = 'Indices'

    def __str__(self):
        return str(self.json)


class DocumentIndexAttachment(models.Model):
    """
    Attachments for one Document.
    """
    index = models.ForeignKey(DocumentIndex, related_name='attachments')
    category = models.SlugField(max_length=20, db_index=True)
    content_type = models.CharField(max_length=255)
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        ordering = ['pk']
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'

    def __str__(self):
        return str(self.data)
