# -*- coding: utf-8 -*-

import re
import os

from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import models
from django.contrib.postgres.fields import DateTimeRangeField, ArrayField

from jane.waveforms.utils import to_datetime

User = settings.AUTH_USER_MODEL


class Path(models.Model):
    name = models.CharField(max_length=255, primary_key=True,
                            validators=['validate_name'])
    ctime = models.DateTimeField()
    mtime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

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
    gaps = models.IntegerField(default=0, db_index=True)
    overlaps = models.IntegerField(default=0, db_index=True)
    format = models.CharField(max_length=255, db_index=True, null=True,
                              blank=True, default=None)
    ctime = models.DateTimeField()
    mtime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']
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


class ContinuousTrace(models.Model):
    file = models.ForeignKey(File, related_name='traces')
    pos = models.IntegerField(default=0)
    network = models.CharField(max_length=2, db_index=True, blank=True)
    station = models.CharField(max_length=5, db_index=True, blank=True)
    location = models.CharField(max_length=2, db_index=True, blank=True)
    channel = models.CharField(max_length=3, db_index=True, blank=True)

    # Original codes for mapped ids.
    original_network = models.CharField(max_length=2, blank=True)
    original_station = models.CharField(max_length=5, blank=True)
    original_location = models.CharField(max_length=2, blank=True)
    original_channel = models.CharField(max_length=3, blank=True)

    timerange = DateTimeRangeField(verbose_name="Temporal Range (UTC)",
                                   db_index=True)
    duration = models.FloatField('Duration (s)', db_index=True, default=0)
    sampling_rate = models.FloatField(default=1)
    npts = models.IntegerField(verbose_name="Samples", default=0)
    preview_trace = ArrayField(base_field=models.FloatField(), blank=True,
                               null=True)
    quality = models.CharField(max_length=1, null=True, blank=True,
                               db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return "%s.%s.%s.%s | %s | %s Hz, %d samples" % (
            self.network, self.station, self.location, self.channel,
            self.timerange, self.sampling_rate, self.npts)

    class Meta:
        ordering = ['-timerange', 'network', 'station', 'location', 'channel']
        unique_together = ['file', 'network', 'station', 'location', 'channel',
                           'timerange']

    def timed_preview_trace(self):
        num_samples = (len(self.preview_trace) - 1)
        delta = (self.timerange.upper - self.timerange.lower) / num_samples
        return [((self.timerange.lower + (delta * i)).isoformat(), v / 2)
                for i, v in enumerate(self.preview_trace)]

    @property
    def seed_id(self):
        return "%s.%s.%s.%s" % (self.network, self.station, self.location,
                                self.channel)

    def save(self, *args, **kwargs):
        if self.pk is None:
            # Never saved before.
            net, sta, loc, cha = self.network, self.station, self.location, \
                                 self.channel
        else:
            # Its an update.
            net, sta, loc, cha = self.original_network, \
                self.original_station, self.original_location, \
                self.original_channel

        # Find the mapping
        query = Mapping.objects.filter(timerange__overlap=self.timerange)
        query = query.filter(network__exact=net,
                             station__exact=sta,
                             channel__exact=cha,
                             location__exact=loc)

        # This is slow for large queries, but we expect the already filtered
        # mapping queryset to always be very small so this should prove no
        # issue.
        full_path = os.path.join(self.file.path.name, self.file.name)
        query = [_i for _i in query if
                 re.match(_i.full_path_regex, full_path)]

        # Raise exception if more than one mapping matches.
        count = len(query)
        if count > 1:
            raise ImproperlyConfigured(
                "More than one mapping found for %s (%s-%s)." % (
                    self.seed_id, self.timerange.lower, self.timerange.upper))
        elif count == 0:
            new_net, new_sta, new_loc, new_cha = net, sta, loc, cha
        else:
            m = query[0]
            new_net, new_sta, new_loc, new_cha = \
                m.new_network, m.new_station, m.new_location, m.new_channel

        self.network = new_net
        self.station = new_sta
        self.location = new_loc
        self.channel = new_cha

        self.original_network = net
        self.original_station = sta
        self.original_location = loc
        self.original_channel = cha

        super().save(*args, **kwargs)

    @classmethod
    def update_all_mappings(cls):
        """
        Has to be called when the mappings have been changed.

        Potentially very slow.

        Returns the total number of updated rows.
        """
        count = 0
        for row in cls.objects.all().iterator():
            row.save()
            count += 1

        return count


class Mapping(models.Model):
    timerange = DateTimeRangeField(verbose_name="Temporal Range (UTC)",
                                   db_index=True)
    network = models.CharField(max_length=2, db_index=True, blank=True)
    station = models.CharField(max_length=5, db_index=True, blank=True)
    location = models.CharField(max_length=2, db_index=True, blank=True)
    channel = models.CharField(max_length=3, db_index=True, blank=True)
    new_network = models.CharField(max_length=2, blank=True)
    new_station = models.CharField(max_length=5, blank=True)
    new_location = models.CharField(max_length=2, blank=True)
    new_channel = models.CharField(max_length=3, blank=True)
    full_path_regex = models.CharField(
        max_length=255, blank=False, default=r"^.*$")
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(User, null=True, editable=False,
                                   related_name='mappings_created')
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    modified_by = models.ForeignKey(User, null=True, editable=False,
                                    related_name='mappings_modified')

    def __str__(self):
        return "%s.%s.%s.%s | %s ==> %s.%s.%s.%s" % (
            self.network, self.station, self.location, self.channel,
            self.timerange, self.new_network, self.new_station,
            self.new_location, self.new_channel)

    class Meta:
        ordering = ['-timerange']

    def clean(self):
        # Make sure no two incompatible mappings are even created.
        if Mapping.objects.filter(timerange__overlap=self.timerange,
                                  network__exact=self.network,
                                  station__exact=self.station,
                                  channel__exact=self.channel,
                                  location__exact=self.location,
                                  full_path_regex__exact=self.full_path_regex
                                  ).count():
            raise ValidationError("This mapping is not compatible with an "
                                  "existing mapping. Check the time range?")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Restriction(models.Model):
    """
    Station/network restrictions of waveforms

    Waveforms are generally seen as public if not listed here.
    """
    help_text = ('Use a single asterisk/star (*) to affect all station '
                 'codes. Use a single asterisk/star in both fields, to '
                 'restrict all network/station code combinations.')
    network = models.CharField(max_length=2, db_index=True,
                               help_text=help_text)
    station = models.CharField(max_length=5, db_index=True,
                               help_text=help_text)
    users = models.ManyToManyField(
        User, db_index=True,
        help_text='The restriction defined by network/station code above will '
                  'apply to all users that are not added here.')
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.ForeignKey(User, null=True, editable=False,
                                   related_name='restrictions_created')
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    modified_by = models.ForeignKey(User, null=True, editable=False,
                                    related_name='restrictions_modified')

    def save(self, *args, **kwargs):
        # ensure uppercase and no whitespaces around network/station ids
        self.network = self.network.upper().strip()
        self.station = self.station.upper().strip()
        super(Restriction, self).save(*args, **kwargs)
