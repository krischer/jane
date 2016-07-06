# -*- coding: utf-8 -*-

import datetime
import os

from django.core.exceptions import ValidationError
from django.test.testcases import TestCase
from psycopg2._range import DateTimeTZRange
import obspy

from jane.waveforms import models
from jane.waveforms.process_waveforms import process_file


class CoreTestCase(TestCase):
    def setUp(self):
        self.path = os.path.abspath(os.path.dirname(__file__))
        self.file = 'test_core.py'

    def test_metadata(self):
        """
        Test extraction of metadata after object creation.
        """
        path_obj = models.Path(name=self.path)
        path_obj.save()
        self.assertTrue(isinstance(path_obj.mtime, datetime.datetime))
        self.assertTrue(isinstance(path_obj.ctime, datetime.datetime))
        file_obj = models.File(path=path_obj, name=self.file)
        file_obj.save()
        self.assertTrue(isinstance(path_obj.mtime, datetime.datetime))
        self.assertTrue(isinstance(path_obj.ctime, datetime.datetime))

    def test_waveform_mappings(self):
        def delete_indexed_waveforms():
            models.File.objects.all().delete()
            assert models.ContinuousTrace.objects.count() == 0

        # Let's use an example file from the fdsnws test suite.
        filename = os.path.join(os.path.dirname(os.path.dirname(self.path)),
                                "fdsnws", "tests", "data", "TA.A25A.mseed")
        assert os.path.exists(filename)

        expected_ids = [
            'TA.A25A..BHE', 'TA.A25A..BHN', 'TA.A25A..BHZ', 'TA.A25A..LCE',
            'TA.A25A..LCQ', 'TA.A25A..LHE', 'TA.A25A..LHN', 'TA.A25A..LHZ',
            'TA.A25A..UHE', 'TA.A25A..UHN', 'TA.A25A..UHZ', 'TA.A25A..VCO',
            'TA.A25A..VEA', 'TA.A25A..VEC', 'TA.A25A..VEP', 'TA.A25A..VHE',
            'TA.A25A..VHN', 'TA.A25A..VHZ', 'TA.A25A..VKI', 'TA.A25A..VM1',
            'TA.A25A..VM2', 'TA.A25A..VM3']

        # Process that file.
        process_file(filename)
        # Make sure it all got stored in the database.
        ids = sorted([_i.seed_id for _i in
                      models.ContinuousTrace.objects.all()])
        self.assertEqual(expected_ids, ids)
        delete_indexed_waveforms()

        # Now create a mapping that does not actually do anything, because
        # it is out of temporal range.
        models.Mapping(
            timerange=DateTimeTZRange(
                obspy.UTCDateTime(2000, 1, 1).datetime,
                obspy.UTCDateTime(2000, 1, 2).datetime),
            network="TA", station="A25A", location="", channel="BHE",
            new_network="XX", new_station="YY", new_location="00",
            new_channel="ZZZ").save()

        # Nothing should have changed.
        process_file(filename)
        ids = sorted([_i.seed_id for _i in
                      models.ContinuousTrace.objects.all()])
        self.assertEqual(expected_ids, ids)
        delete_indexed_waveforms()

        # Now create a mapping that does something.
        models.Mapping(
            timerange=DateTimeTZRange(
                obspy.UTCDateTime(2002, 1, 1).datetime,
                obspy.UTCDateTime(2016, 1, 2).datetime),
            network="TA", station="A25A", location="", channel="BHE",
            new_network="XX", new_station="YY", new_location="00",
            new_channel="ZZZ").save()

        # Nothing should have changed.
        process_file(filename)
        ids = sorted([_i.seed_id for _i in
                      models.ContinuousTrace.objects.all()])
        self.assertEqual(len(ids), len(expected_ids))
        self.assertIn("XX.YY.00.ZZZ", ids)
        self.assertNotIn("TA.A25A..BHE", ids)

        # Now remove the mappings and test the reindexing!
        models.Mapping.objects.all().delete()

        # Without reindex, nothing changed.
        ids = sorted([_i.seed_id for _i in
                      models.ContinuousTrace.objects.all()])
        self.assertEqual(len(ids), len(expected_ids))
        self.assertIn("XX.YY.00.ZZZ", ids)
        self.assertNotIn("TA.A25A..BHE", ids)

        # Now reindex - it should have changed.
        models.ContinuousTrace.update_all_mappings()
        ids = sorted([_i.seed_id for _i in
                      models.ContinuousTrace.objects.all()])
        self.assertEqual(expected_ids, ids)
        delete_indexed_waveforms()

    def test_creation_of_mappings(self):
        # First create two compatible ones.
        models.Mapping(
            timerange=DateTimeTZRange(
                obspy.UTCDateTime(2000, 1, 1).datetime,
                obspy.UTCDateTime(2001, 1, 2).datetime),
            network="TA", station="A25A", location="", channel="BHE",
            new_network="XX", new_station="YY", new_location="00",
            new_channel="ZZZ").save()
        models.Mapping(
            timerange=DateTimeTZRange(
                obspy.UTCDateTime(2005, 1, 1).datetime,
                obspy.UTCDateTime(2006, 1, 2).datetime),
            network="TA", station="A25A", location="", channel="BHE",
            new_network="XX", new_station="YY", new_location="00",
            new_channel="ZZZ").save()

        # Add another one with an overlapping mapping - should raise.
        with self.assertRaises(ValidationError):
            models.Mapping(
                timerange=DateTimeTZRange(
                    obspy.UTCDateTime(2000, 1, 1).datetime,
                    obspy.UTCDateTime(2012, 1, 2).datetime),
                network="TA", station="A25A", location="",
                channel="BHE", new_network="XX", new_station="YY",
                new_location="00", new_channel="ZZZ").save()
