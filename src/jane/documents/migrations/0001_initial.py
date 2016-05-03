# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.gis.db.models.fields
from django.contrib.postgres.fields import jsonb
from django.db import models, migrations
import djangoplugins.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('djangoplugins', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('content_type', models.CharField(max_length=255)),
                ('data', models.BinaryField()),
                ('filesize', models.IntegerField(editable=False)),
                ('sha1', models.CharField(unique=True, db_index=True, max_length=40, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='documents_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Document',
                'ordering': ['pk'],
                'verbose_name_plural': 'Documents',
            },
        ),
        migrations.CreateModel(
            name='DocumentIndex',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('json', jsonb.JSONField(verbose_name='JSON')),
                ('geometry', django.contrib.gis.db.models.fields.GeometryCollectionField(srid=4326, geography=True, blank=True, null=True)),
                ('document', models.ForeignKey(related_name='indices', to='documents.Document')),
            ],
            options={
                'verbose_name': 'Index',
                'ordering': ['pk'],
                'verbose_name_plural': 'Indices',
            },
        ),
        migrations.CreateModel(
            name='DocumentIndexAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('category', models.CharField(db_index=True, max_length=50)),
                ('content_type', models.CharField(max_length=255)),
                ('data', models.BinaryField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='attachments_created', to=settings.AUTH_USER_MODEL)),
                ('index', models.ForeignKey(related_name='attachments', to='documents.DocumentIndex')),
                ('modified_by', models.ForeignKey(related_name='attachments_modified', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Attachment',
                'ordering': ['pk'],
                'verbose_name_plural': 'Attachments',
            },
        ),
        migrations.CreateModel(
            name='DocumentType',
            fields=[
                ('name', models.SlugField(primary_key=True, max_length=20, serialize=False)),
                ('definition', djangoplugins.fields.PluginField(related_name='definition', to='djangoplugins.Plugin')),
                ('indexer', djangoplugins.fields.PluginField(related_name='indexer', to='djangoplugins.Plugin')),
                ('retrieve_permissions', djangoplugins.fields.ManyPluginField(blank=True, related_name='retrieve_permissions', to='djangoplugins.Plugin')),
                ('upload_permissions', djangoplugins.fields.ManyPluginField(blank=True, related_name='upload_permissions', to='djangoplugins.Plugin')),
                ('validators', djangoplugins.fields.ManyPluginField(blank=True, related_name='validators', to='djangoplugins.Plugin')),
            ],
            options={
                'verbose_name': 'Document Type',
                'ordering': ['name'],
                'verbose_name_plural': 'Document Types',
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
