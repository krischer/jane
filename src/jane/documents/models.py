# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from djangoplugins.fields import PluginField, ManyPluginField
from jsonfield.fields import JSONField

from jane.documents import plugins


class DocumentType(models.Model):
    """
    Document category. Will be determined from the registered plugins.
    """
    name = models.SlugField(max_length=20, primary_key=True)
    content_type = models.CharField(max_length=255)
    # plugins
    indexer = ManyPluginField(plugins.IndexerPluginPoint, null=True,
        blank=True, related_name='indexers')
    validators = ManyPluginField(plugins.ValidatorPluginPoint, null=True,
        blank=True, related_name='validators')
    converters = ManyPluginField(plugins.ConverterPluginPoint, null=True,
        blank=True, related_name='converters')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


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


class DocumentRevision(models.Model):
    """
    A certain document revision.
    """
    document = models.ForeignKey(Document, related_name='document_revisions')
    revision = models.IntegerField(default=0, db_index=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    data = models.BinaryField()
    filesize = models.IntegerField()
    sha1 = models.CharField(max_length=40, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(User, null=True, editable=False,
            related_name='document_revisions_created')
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    modified_by = models.ForeignKey(User, null=True, editable=False,
            related_name='documents_revisions_modified')

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ['pk']
        unique_together = ['document', 'revision']
        verbose_name = 'DocumentRevision'
        verbose_name_plural = 'DocumentRevisions'

    def save(self, *args, **kwargs):
        super(DocumentRevision, self).save(*args, **kwargs)


class _DocumentRevisionIndexManager(models.GeoManager):
    """
    Custom queryset manager for the document revision indices.
    """
    def get_queryset(self):
        """
        """
        return super(_DocumentRevisionIndexManager, self).get_queryset().\
            select_related('document_revision_attachments').\
            prefetch_related('document_revision_attachments')


class DocumentRevisionIndex(models.Model):
    """
    Indexed values for a specific revision of a document.
    """
    document = models.ForeignKey(DocumentRevision,
                                 related_name='document_revision_indices')
    json = JSONField(verbose_name="JSON")
    geometry = models.GeometryCollectionField(blank=True, null=True,
        geography=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    objects = _DocumentRevisionIndexManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'DocumentRevisionIndex'
        verbose_name_plural = 'DocumentRevisionIndices'

    def __str__(self):
        return str(self.json)


class DocumentRevisionAttachment(models.Model):
    """
    Attachments for one DocumentRevisonIndex.
    """
    document_revision_index = models.ForeignKey(
        DocumentRevisionIndex, related_name='document_revision_attachments')
    category = models.SlugField(max_length=20, db_index=True)
    content_type = models.CharField(max_length=255)
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return str(self.data)
