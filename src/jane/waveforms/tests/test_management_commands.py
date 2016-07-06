# -*- coding: utf-8 -*-

import io
import tempfile

import obspy

from django.core.management import call_command
from django.test.testcases import TestCase

from jane.waveforms import models


class ManagementCommandTestCase(TestCase):
    def test_add_mappings(self):
        """
        Tests the add_mappings command.
        """
        self.assertEqual(models.Mapping.objects.count(), 0)

        with io.StringIO() as out:
            with tempfile.NamedTemporaryFile("wt") as f:
                f.write("AA.BB.CC.DD EE.FF.GG.HH 2016-01-01 2016-01-02\n")
                f.write("A1.B1.C1.D1 E1.F1.G1.H1 2016-01-02 2016-01-03\n")
                f.seek(0, 0)
                call_command('add_mappings', f.name, stdout=out, stderr=out)

            out.seek(0, 0)
            out = out.read()

        self.assertIn(
            "Created mapping 'AA.BB.CC.DD EE.FF.GG.HH 2016-01-01 2016-01-02'",
            out)
        self.assertIn(
            "Created mapping 'A1.B1.C1.D1 E1.F1.G1.H1 2016-01-02 2016-01-03'",
            out)

        # Make sure it did get created.
        self.assertEqual(models.Mapping.objects.count(), 2)

        m = models.Mapping.objects.filter(network="A1").first()
        self.assertEqual((m.network, m.station, m.location, m.channel),
                         ("A1", "B1", "C1", "D1"))
        self.assertEqual((m.new_network, m.new_station, m.new_location,
                          m.new_channel),
                         ("E1", "F1", "G1", "H1"))
        self.assertEqual(m.timerange.lower,
                         obspy.UTCDateTime(2016, 1, 2).datetime)
        self.assertEqual(m.timerange.upper,
                         obspy.UTCDateTime(2016, 1, 3).datetime)

        # Running the command again will only mean that the mappings are
        # skipped.
        with io.StringIO() as out:
            with tempfile.NamedTemporaryFile("wt") as f:
                # Test that comments are skipped.
                f.write("# Random comment\n")
                f.write("AA.BB.CC.DD EE.FF.GG.HH 2016-01-01 2016-01-02\n")
                f.write("A1.B1.C1.D1 E1.F1.G1.H1 2016-01-02 2016-01-03\n")
                f.seek(0, 0)
                call_command('add_mappings', f.name, stdout=out, stderr=out)

            out.seek(0, 0)
            out = out.read()

        self.assertIn(
            "Mapping 'AA.BB.CC.DD EE.FF.GG.HH 2016-01-01 2016-01-02' already "
            "exists. Skipping.", out)
        self.assertIn(
            "Mapping 'A1.B1.C1.D1 E1.F1.G1.H1 2016-01-02 2016-01-03' already "
            "exists. Skipping.", out)

        # Nothing changed.
        self.assertEqual(models.Mapping.objects.count(), 2)
