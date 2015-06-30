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
                ('network', models.CharField(max_length=2, blank=True, db_index=True)),
                ('station', models.CharField(max_length=5, blank=True, db_index=True)),
                ('location', models.CharField(max_length=2, blank=True, db_index=True)),
                ('channel', models.CharField(max_length=3, blank=True, db_index=True)),
                ('timerange', django.contrib.postgres.fields.ranges.DateTimeRangeField(db_index=True, verbose_name='Temporal Range (UTC)')),
                ('duration', models.FloatField(verbose_name='Duration (s)', db_index=True, default=0)),
                ('sampling_rate', models.FloatField(default=1)),
                ('npts', models.IntegerField(verbose_name='Samples', default=0)),
                ('preview_trace', django.contrib.postgres.fields.ArrayField(size=None, base_field=models.FloatField())),
                ('quality', models.CharField(max_length=1, blank=True, db_index=True, null=True)),
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
                ('name', models.CharField(max_length=255, db_index=True)),
                ('size', models.IntegerField()),
                ('gaps', models.IntegerField(db_index=True, default=0)),
                ('overlaps', models.IntegerField(db_index=True, default=0)),
                ('format', models.CharField(max_length=255, blank=True, default=None, db_index=True, null=True)),
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
                ('created_by', models.ForeignKey(related_name='mappings_created', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('modified_by', models.ForeignKey(related_name='mappings_modified', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['-timerange'],
            },
        ),
        migrations.CreateModel(
            name='Path',
            fields=[
                ('name', models.CharField(validators=['validate_name'], max_length=255, serialize=False, primary_key=True)),
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
                ('network', models.CharField(max_length=2, db_index=True)),
                ('station', models.CharField(max_length=5, db_index=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='restrictions_created', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('modified_by', models.ForeignKey(related_name='restrictions_modified', editable=False, to=settings.AUTH_USER_MODEL, null=True)),
                ('users', models.ManyToManyField(to=settings.AUTH_USER_MODEL, db_index=True)),
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
