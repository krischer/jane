# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.ranges
import jsonfield.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContinuousTrace',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('pos', models.IntegerField(default=0)),
                ('network', models.CharField(db_index=True, blank=True, max_length=2)),
                ('station', models.CharField(db_index=True, blank=True, max_length=5)),
                ('location', models.CharField(db_index=True, blank=True, max_length=2)),
                ('channel', models.CharField(db_index=True, blank=True, max_length=3)),
                ('timerange', django.contrib.postgres.fields.ranges.DateTimeRangeField(verbose_name='Temporal Range (UTC)', db_index=True)),
                ('duration', models.FloatField(default=0, verbose_name='Duration (s)', db_index=True)),
                ('calib', models.FloatField(default=1, verbose_name='Calibration factor')),
                ('sampling_rate', models.FloatField(default=1)),
                ('npts', models.IntegerField(default=0, verbose_name='Samples')),
                ('preview_trace', jsonfield.fields.JSONField(null=True)),
                ('preview_image', models.BinaryField(null=True)),
                ('quality', models.CharField(null=True, db_index=True, blank=True, max_length=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-timerange', 'network', 'station', 'location', 'channel'],
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('name', models.CharField(max_length=255, db_index=True)),
                ('size', models.IntegerField()),
                ('gaps', models.IntegerField(default=0, db_index=True)),
                ('overlaps', models.IntegerField(default=0, db_index=True)),
                ('format', models.CharField(default=None, null=True, db_index=True, blank=True, max_length=255)),
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
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('timerange', django.contrib.postgres.fields.ranges.DateTimeRangeField(verbose_name='Temporal Range (UTC)', db_index=True)),
                ('network', models.CharField(blank=True, max_length=2)),
                ('station', models.CharField(blank=True, max_length=5)),
                ('location', models.CharField(blank=True, max_length=2)),
                ('channel', models.CharField(blank=True, max_length=3)),
                ('new_network', models.CharField(blank=True, max_length=2)),
                ('new_station', models.CharField(blank=True, max_length=5)),
                ('new_location', models.CharField(blank=True, max_length=2)),
                ('new_channel', models.CharField(blank=True, max_length=3)),
                ('path_regex', models.CharField(blank=True, max_length=255)),
                ('file_regex', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(editable=False, null=True, related_name='mappings_created', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(editable=False, null=True, related_name='mappings_modified', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-timerange'],
            },
        ),
        migrations.CreateModel(
            name='Path',
            fields=[
                ('name', models.CharField(validators=['validate_name'], serialize=False, primary_key=True, max_length=255)),
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
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('network', models.CharField(max_length=2, db_index=True)),
                ('station', models.CharField(max_length=5, db_index=True)),
                ('comment', models.TextField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(editable=False, null=True, related_name='restrictions_created', to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(editable=False, null=True, related_name='restrictions_modified', to=settings.AUTH_USER_MODEL)),
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
