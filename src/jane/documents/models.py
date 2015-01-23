# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
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
    content_type = models.CharField(max_length=255)
    # plugins
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
        verbose_name = 'Type'
        verbose_name_plural = 'Types'


class Document(models.Model):
    """
    One document. Can have multiple revisions.
    """
    document_type = models.ForeignKey(DocumentType, related_name='documents')
    name = models.SlugField(max_length=255, null=True, blank=True,
                            db_index=True)

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ['pk']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'


class DocumentRevision(models.Model):
    """
    A certain document revision_number.
    """
    document = models.ForeignKey(Document, related_name='revisions')
    revision_number = models.IntegerField(default=0, db_index=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    data = models.BinaryField()
    filesize = models.IntegerField()
    sha1 = models.CharField(max_length=40, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(User, null=True, editable=False,
                                   related_name='revisions_created')
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    modified_by = models.ForeignKey(User, null=True, editable=False,
                                    related_name='revisions_modified')

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ['pk']
        unique_together = ['document', 'revision_number']
        verbose_name = 'Revision'
        verbose_name_plural = 'Revisions'

    def save(self, *args, **kwargs):
        super(DocumentRevision, self).save(*args, **kwargs)


class _DocumentRevisionIndexManager(models.GeoManager):
    """
    Custom queryset manager for the document revision_number indices.
    """
    def get_queryset(self):
        """
        """
        return super(_DocumentRevisionIndexManager, self).get_queryset().\
            select_related('attachments').\
            prefetch_related('attachments')


class DocumentRevisionIndex(models.Model):
    """
    Indexed values for a specific revision_number of a document.
    """
    revision = models.ForeignKey(
        DocumentRevision, related_name='indices')
    json = PostgreSQLJsonField(verbose_name="JSON")
    geometry = models.GeometryCollectionField(blank=True, null=True,
                                              geography=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    objects = _DocumentRevisionIndexManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Index'
        verbose_name_plural = 'Indices'

    def __str__(self):
        return str(self.json)


class DocumentRevisionIndexAttachment(models.Model):
    """
    Attachments for one DocumentRevisonIndex.
    """
    index = models.ForeignKey(DocumentRevisionIndex,
                              related_name='attachments')
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
