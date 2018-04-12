# -*- coding: utf-8 -*-
"""
Add waveform mappings in bulk.
"""
import obspy
from psycopg2._range import DateTimeTZRange

import django
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from jane.waveforms.models import Mapping


django.setup()


class Command(BaseCommand):
    help = "Add waveform mappings in bulk with specification in a file."

    def add_arguments(self, parser):
        parser.add_argument("mappings_file", type=str, help="""
        File containing the definitions of a number of mappings. Each line
        defines one mapping and it has to be in the form `NET.STA.LOC.CHA
        NEW_NET.NEW_STA.NEW_LOC.NEW_CHA STARTTIME ENDTIME`.
        """)

    def handle(self, *args, **kwargs):
        mappings_file = kwargs["mappings_file"]
        with open(mappings_file, "rt") as fh:
            count = 0
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                from_id, to_id, start, end = line.split()

                try:
                    from_net, from_sta, from_loc, from_cha = from_id.split(".")
                except Exception:
                    msg = "From id '%s' is not acceptable SEED id." % from_id
                    raise Exception(msg)
                try:
                    to_net, to_sta, to_loc, to_cha = to_id.split(".")
                except Exception:
                    msg = "From id '%s' is not acceptable SEED id." % to_id
                    raise Exception(msg)

                try:
                    start = obspy.UTCDateTime(start)
                except Exception:
                    msg = "Start time '%s' cannot be parsed." % start
                    raise Exception(msg)
                try:
                    end = obspy.UTCDateTime(end)
                except Exception:
                    msg = "End time '%s' cannot be parsed." % end
                    raise Exception(msg)

                start = start.datetime
                end = end.datetime

                params = {
                    "timerange": DateTimeTZRange(start, end),
                    "network": from_net,
                    "station": from_sta,
                    "location": from_loc,
                    "channel": from_cha,
                    "new_network": to_net,
                    "new_station": to_sta,
                    "new_location": to_loc,
                    "new_channel": to_cha,
                }

                # Check if the mapping already exists.
                if Mapping.objects.filter(**params).count():
                    self.stdout.write(
                        "Mapping '%s' already exists. Skipping.\n" % line)
                    continue

                # Now try to save the new mapping.
                try:
                    Mapping(**params).save()
                except ValidationError:
                    msg = (
                        "Failed to add mapping '%s' as it is not compatible "
                        "with an existing mapping. Check the time range? "
                        "Overlaps are not allowed.") % line
                    raise Exception(msg)

                self.stdout.write("Created mapping '%s'.\n" % line)
                count += 1

        self.stdout.write("\nSuccessfully created %i mapping.\n" % count)

        if count:
            self.stdout.write(
                "\nIf you want to apply the mappings to existing files, "
                "make sure to update the waveform indices via the "
                "'Mappings' panel in the admin interface.")
