# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields
import jane.documents.models
import djangoplugins.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('djangoplugins', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('name', models.SlugField(max_length=255)),
                ('content_type', models.CharField(max_length=255)),
                ('data', models.BinaryField()),
                ('filesize', models.IntegerField(editable=False)),
                ('sha1', models.CharField(unique=True, db_index=True, editable=False, max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='documents_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Documents',
                'verbose_name': 'Document',
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='DocumentIndex',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('json', jane.documents.models.PostgreSQLJSONBField(verbose_name='JSON')),
                ('geometry', django.contrib.gis.db.models.fields.GeometryCollectionField(geography=True, blank=True, srid=4326, null=True)),
                ('document', models.ForeignKey(related_name='indices', to='documents.Document')),
            ],
            options={
                'verbose_name_plural': 'Indices',
                'verbose_name': 'Index',
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='DocumentIndexAttachment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('category', models.SlugField(max_length=20)),
                ('content_type', models.CharField(max_length=255)),
                ('data', models.BinaryField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='attachments_created', to=settings.AUTH_USER_MODEL)),
                ('index', models.ForeignKey(related_name='attachments', to='documents.DocumentIndex')),
                ('modified_by', models.ForeignKey(related_name='attachments_modified', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Attachments',
                'verbose_name': 'Attachment',
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='DocumentType',
            fields=[
                ('name', models.SlugField(primary_key=True, serialize=False, max_length=20)),
                ('definition', djangoplugins.fields.PluginField(related_name='definition', to='djangoplugins.Plugin')),
                ('indexer', djangoplugins.fields.PluginField(related_name='indexer', to='djangoplugins.Plugin')),
                ('retrieve_permissions', djangoplugins.fields.ManyPluginField(related_name='retrieve_permissions', blank=True, to='djangoplugins.Plugin')),
                ('upload_permissions', djangoplugins.fields.ManyPluginField(related_name='upload_permissions', blank=True, to='djangoplugins.Plugin')),
                ('validators', djangoplugins.fields.ManyPluginField(related_name='validators', blank=True, to='djangoplugins.Plugin')),
            ],
            options={
                'verbose_name_plural': 'Document Types',
                'verbose_name': 'Document Type',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='document',
            name='document_type',
            field=models.ForeignKey(related_name='documents', to='documents.DocumentType'),
        ),
        migrations.AddField(
            model_name='document',
            name='modified_by',
            field=models.ForeignKey(related_name='documents_modified', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='document',
            unique_together=set([('document_type', 'name')]),
        ),
    ]
