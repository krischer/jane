# -*- coding: utf-8 -*-

from django.db import models
from djangoplugins.fields import PluginField, ManyPluginField
from pymongo import MongoClient

from jane.documents import plugins


mongo_db = MongoClient().jane


class ResourceType(models.Model):
    XML_CONTENT = 0
    JSON_CONTENT = 1
    TEXT_CONTENT = 2
    BINARY_CONTENT = 3

    CONTENT_TYPE_CHOICES = [
        (XML_CONTENT, 'xml'),
        (JSON_CONTENT, 'json'),
        (TEXT_CONTENT, 'text'),
        (BINARY_CONTENT, 'binary'),
    ]

    name = models.SlugField(max_length=20, primary_key=True)
    content_type = models.IntegerField(choices=CONTENT_TYPE_CHOICES)
    indexer = PluginField(plugins.IndexerPluginPoint, null=True,
        blank=True, related_name='indexer')
    validators = ManyPluginField(plugins.ValidatorPluginPoint, null=True,
        blank=True, related_name='validators')
    converters = ManyPluginField(plugins.ConverterPluginPoint, null=True,
        blank=True, related_name='converters')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Resource(models.Model):
    resource_type = models.ForeignKey(ResourceType, related_name='resources')
    name = models.SlugField(max_length=20, null=True, blank=True,
        db_index=True)

    def __unicode__(self):
        return u"%s" % (self.pk)

    class Meta:
        ordering = ['pk']


class Document(models.Model):
    resource = models.ForeignKey(Resource, related_name='documents')
    revision = models.IntegerField(default=0)
    filename = models.CharField(max_length=255)
    data = models.BinaryField()
    filesize = models.IntegerField()
    sha1 = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)

    def __unicode__(self):
        return u"%s" % (self.pk)

    class Meta:
        ordering = ['pk']
        unique_together = ['resource', 'revision']

    @property
    def collection(self):
        name = self.resource.resource_type.name
        return mongo_db[name]

    def save(self, *args, **kwargs):
        super(Document, self).save(*args, **kwargs)
        # store index into mongo db
        self.collection.insert({
            '_id': self.pk,
            'filename': self.filename,
            'filesize': self.filesize,
            'sha1': self.sha1})

    def format_data(self):
        return self.collection.find_one({"_id": self.pk})
