# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from djangoplugins.fields import PluginField, ManyPluginField
from jsonfield.fields import JSONField

from jane.documents import plugins


class ResourceType(models.Model):
    name = models.SlugField(max_length=20, primary_key=True)
    content_type = models.CharField(max_length=255)
    # plugins
    indexer = PluginField(plugins.IndexerPluginPoint, null=True,
        blank=True, related_name='indexer')
    validators = ManyPluginField(plugins.ValidatorPluginPoint, null=True,
        blank=True, related_name='validators')
    converters = ManyPluginField(plugins.ConverterPluginPoint, null=True,
        blank=True, related_name='converters')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Resource(models.Model):
    resource_type = models.ForeignKey(ResourceType, related_name='resources')
    name = models.SlugField(max_length=255, null=True, blank=True,
        db_index=True)

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ['pk']


class Document(models.Model):
    """
    A resource revision
    """
    resource = models.ForeignKey(Resource, related_name='documents')
    revision = models.IntegerField(default=0, db_index=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    data = models.BinaryField()
    filesize = models.IntegerField()
    sha1 = models.CharField(max_length=40, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(User, null=True, editable=False,
            related_name='documents_created')
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    modified_by = models.ForeignKey(User, null=True, editable=False,
            related_name='documents_modified')

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ['pk']
        unique_together = ['resource', 'revision']
        verbose_name = 'Revision'
        verbose_name_plural = 'Revisions'

    def save(self, *args, **kwargs):
        super(Document, self).save(*args, **kwargs)


class RecordManager(models.GeoManager):

    def get_queryset(self):
        """
        """
        return super(RecordManager, self).get_queryset().\
            select_related('attachments').\
            prefetch_related('attachments')


class Record(models.Model):
    document = models.ForeignKey(Document, related_name='records')
    json = JSONField(verbose_name="JSON")
    geometry = models.GeometryCollectionField(blank=True, null=True,
        geography=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    objects = RecordManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Index'
        verbose_name_plural = 'Indexes'

    def __str__(self):
        return str(self.json)


class Attachment(models.Model):
    record = models.ForeignKey(Record, related_name='attachments')
    category = models.SlugField(max_length=20, db_index=True)
    content_type = models.CharField(max_length=255)
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        ordering = ['pk']

    def __str__(self):
        return str(self.data)
