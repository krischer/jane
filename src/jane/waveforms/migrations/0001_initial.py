# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContinuousTrace',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('pos', models.IntegerField(default=0)),
                ('network', models.CharField(blank=True, max_length=2, db_index=True)),
                ('station', models.CharField(blank=True, max_length=5, db_index=True)),
                ('location', models.CharField(blank=True, max_length=2, db_index=True)),
                ('channel', models.CharField(blank=True, max_length=3, db_index=True)),
                ('starttime', models.DateTimeField(db_index=True, verbose_name='Start time (UTC)')),
                ('endtime', models.DateTimeField(db_index=True, verbose_name='End time (UTC)')),
                ('duration', models.FloatField(default=0, verbose_name='Duration (s)', db_index=True)),
                ('calib', models.FloatField(default=1, verbose_name='Calibration factor')),
                ('sampling_rate', models.FloatField(default=1)),
                ('npts', models.IntegerField(default=0, verbose_name='Samples')),
                ('preview_trace', jsonfield.fields.JSONField(null=True)),
                ('preview_image', models.BinaryField(null=True)),
                ('quality', models.CharField(blank=True, max_length=1, null=True, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-starttime', '-endtime', 'network', 'station', 'location', 'channel'],
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('size', models.IntegerField()),
                ('gaps', models.IntegerField(default=0, db_index=True)),
                ('overlaps', models.IntegerField(default=0, db_index=True)),
                ('format', models.CharField(db_index=True, blank=True, max_length=255, null=True, default=None)),
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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('starttime', models.DateTimeField(db_index=True, verbose_name='Start time (UTC)')),
                ('endtime', models.DateTimeField(db_index=True, verbose_name='End time (UTC)')),
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
                ('created_by', models.ForeignKey(related_name='mappings_created', editable=False, null=True, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='mappings_modified', editable=False, null=True, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-starttime', '-endtime'],
            },
        ),
        migrations.CreateModel(
            name='Path',
            fields=[
                ('name', models.CharField(primary_key=True, max_length=255, serialize=False, validators=['validate_name'])),
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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('network', models.CharField(db_index=True, max_length=2)),
                ('station', models.CharField(db_index=True, max_length=5)),
                ('comment', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(related_name='restrictions_created', editable=False, null=True, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(related_name='restrictions_modified', editable=False, null=True, to=settings.AUTH_USER_MODEL)),
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
            unique_together=set([('file', 'network', 'station', 'location', 'channel', 'starttime', 'endtime')]),
        ),
    ]
