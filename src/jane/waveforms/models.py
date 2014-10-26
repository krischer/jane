# -*- coding: utf-8 -*-

import os

from django.db import models
from django.core.exceptions import ValidationError

from jane.waveforms.utils import to_datetime


class Path(models.Model):
    name = models.CharField(max_length=255, primary_key=True,
        validators=['validate_name'])
    ctime = models.DateTimeField()
    mtime = models.DateTimeField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

    def validate_name(self, value):
        if not os.path.isdir(value):
            raise ValidationError(u'%s is not a valid path' % value)
        if not os.path.isabs(value):
            raise ValidationError(u'%s is not a absolute path' % value)

    def save(self, *args, **kwargs):
        stats = os.stat(self.name)
        self.mtime = to_datetime(stats.st_mtime)
        self.ctime = to_datetime(stats.st_ctime)
        super(Path, self).save(*args, **kwargs)


class File(models.Model):
    path = models.ForeignKey(Path, related_name='files')
    name = models.CharField(max_length=255, db_index=True)
    size = models.IntegerField()
    category = models.IntegerField(default=-1, db_index=True)
    format = models.CharField(max_length=255, db_index=True, null=True,
        blank=True, default=None)
    ctime = models.DateTimeField()
    mtime = models.DateTimeField()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['path', 'name']
        unique_together = ['path', 'name']

    @property
    def absolute_path(self):
        return os.path.join(self.path.name, self.name)

    def save(self, *args, **kwargs):
        stats = os.stat(self.absolute_path)
        self.mtime = to_datetime(stats.st_mtime)
        self.ctime = to_datetime(stats.st_ctime)
        self.size = int(stats.st_size)
        super(File, self).save(*args, **kwargs)


class Channel(models.Model):
    file = models.ForeignKey(File, related_name='waveforms')
    network = models.CharField(max_length=2, db_index=True, blank=True)
    station = models.CharField(max_length=5, db_index=True, blank=True)
    location = models.CharField(max_length=2, db_index=True, blank=True)
    channel = models.CharField(max_length=3, db_index=True, blank=True)
    starttime = models.DateTimeField(verbose_name="Start time (UTC)",
        db_index=True)
    endtime = models.DateTimeField(verbose_name="End time (UTC)",
        db_index=True)
    calib = models.FloatField(verbose_name="Calibration factor", default=1)
    sampling_rate = models.FloatField(default=1)
    npts = models.IntegerField(verbose_name="Samples", default=0)
    preview_trace = models.BinaryField(null=True)
    preview_image = models.BinaryField(null=True)

    def __str__(self):
        return "%s.%s.%s.%s | %s - %s | %s Hz, %d samples" % (self.network,
            self.station, self.location, self.channel, self.starttime,
            self.endtime, self.sampling_rate, self.npts)

    class Meta:
        ordering = ['-starttime', '-endtime', 'network', 'station',
            'location', 'channel']
        unique_together = ['file', 'network', 'station', 'location', 'channel',
            'starttime', 'endtime']


class GapOverlap(models.Model):
    channel = models.ForeignKey(Channel, related_name='gaps')
    gap = models.BooleanField(db_index=True, default=True)
    starttime = models.DateTimeField(db_index=True)
    endtime = models.DateTimeField(db_index=True)
    samples = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Gap/Overlap'
        verbose_name_plural = 'Gaps/Overlaps'
        ordering = ['-starttime', '-endtime']


class Mapping(models.Model):
    starttime = models.DateTimeField(verbose_name="Start time (UTC)",
        db_index=True)
    endtime = models.DateTimeField(verbose_name="End time (UTC)",
        db_index=True)
    network = models.CharField(max_length=2, blank=True)
    station = models.CharField(max_length=5, blank=True)
    location = models.CharField(max_length=2, blank=True)
    channel = models.CharField(max_length=3, blank=True)
    new_network = models.CharField(max_length=2, blank=True)
    new_station = models.CharField(max_length=5, blank=True)
    new_location = models.CharField(max_length=2, blank=True)
    new_channel = models.CharField(max_length=3, blank=True)
    path_regex = models.CharField(max_length=255, blank=True)
    file_regex = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return "%s.%s.%s.%s | %s - %s ==> %s.%s.%s.%s" % (self.network,
            self.station, self.location, self.channel, self.starttime,
            self.endtime, self.new_network, self.new_station,
            self.new_location, self.new_channel)

    class Meta:
        ordering = ['-starttime', '-endtime']
