# -*- coding: utf-8 -*-

from django.db import models
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
    resource = models.ForeignKey(Resource, related_name='documents')
    revision = models.IntegerField(default=0, db_index=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    data = models.BinaryField()
    filesize = models.IntegerField()
    sha1 = models.CharField(max_length=40, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        ordering = ['pk']
        unique_together = ['resource', 'revision']

    def save(self, *args, **kwargs):
        super(Document, self).save(*args, **kwargs)


class IndexedValue(models.Model):
    document = models.ForeignKey(Document, related_name='indexed_values')
    json = JSONField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return str(self.json)

    class Meta:
        ordering = ['pk']
