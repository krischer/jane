# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.ranges
import django.contrib.postgres.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContinuousTrace',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('pos', models.IntegerField(default=0)),
                ('network', models.CharField(db_index=True, max_length=2, blank=True)),
                ('station', models.CharField(db_index=True, max_length=5, blank=True)),
                ('location', models.CharField(db_index=True, max_length=2, blank=True)),
                ('channel', models.CharField(db_index=True, max_length=3, blank=True)),
                ('timerange', django.contrib.postgres.fields.ranges.DateTimeRangeField(db_index=True, verbose_name='Temporal Range (UTC)')),
                ('duration', models.FloatField(db_index=True, default=0, verbose_name='Duration (s)')),
                ('sampling_rate', models.FloatField(default=1)),
                ('npts', models.IntegerField(default=0, verbose_name='Samples')),
                ('preview_trace', django.contrib.postgres.fields.ArrayField(null=True, size=None, blank=True, base_field=models.FloatField())),
                ('quality', models.CharField(db_index=True, max_length=1, blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-timerange', 'network', 'station', 'location', 'channel'],
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('size', models.IntegerField()),
                ('gaps', models.IntegerField(db_index=True, default=0)),
                ('overlaps', models.IntegerField(db_index=True, default=0)),
                ('format', models.CharField(db_index=True, default=None, max_length=255, blank=True, null=True)),
                ('ctime', models.DateTimeField()),
                ('mtime', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Mapping',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('timerange', django.contrib.postgres.fields.ranges.DateTimeRangeField(db_index=True, verbose_name='Temporal Range (UTC)')),
                ('network', models.CharField(max_length=2, blank=True)),
                ('station', models.CharField(max_length=5, blank=True)),
                ('location', models.CharField(max_length=2, blank=True)),
                ('channel', models.CharField(max_length=3, blank=True)),
                ('new_network', models.CharField(max_length=2, blank=True)),
                ('new_station', models.CharField(max_length=5, blank=True)),
                ('new_location', models.CharField(max_length=2, blank=True)),
                ('new_channel', models.CharField(max_length=3, blank=True)),
                ('path_regex', models.CharField(max_length=255, blank=True)),
                ('file_regex', models.CharField(max_length=255, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, editable=False, related_name='mappings_created')),
                ('modified_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, editable=False, related_name='mappings_modified')),
            ],
            options={
                'ordering': ['-timerange'],
            },
        ),
        migrations.CreateModel(
            name='Path',
            fields=[
                ('name', models.CharField(max_length=255, validators=['validate_name'], serialize=False, primary_key=True)),
                ('ctime', models.DateTimeField()),
                ('mtime', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Restriction',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('network', models.CharField(db_index=True, max_length=2)),
                ('station', models.CharField(db_index=True, max_length=5)),
                ('comment', models.TextField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, editable=False, related_name='restrictions_created')),
                ('modified_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, editable=False, related_name='restrictions_modified')),
                ('users', models.ManyToManyField(db_index=True, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='file',
            name='path',
            field=models.ForeignKey(related_name='files', to='waveforms.Path'),
        ),
        migrations.AddField(
            model_name='continuoustrace',
            name='file',
            field=models.ForeignKey(related_name='traces', to='waveforms.File'),
        ),
        migrations.AlterUniqueTogether(
            name='file',
            unique_together=set([('path', 'name')]),
        ),
        migrations.AlterUniqueTogether(
            name='continuoustrace',
            unique_together=set([('file', 'network', 'station', 'location', 'channel', 'timerange')]),
        ),
    ]
