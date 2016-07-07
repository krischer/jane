# -*- coding: utf-8 -*-

import os

from django.contrib.gis.geos.point import Point
from django.test import TestCase

from jane.quakeml.plugins import QuakeMLIndexerPlugin


PATH = os.path.join(os.path.dirname(__file__), 'data')
FILES = {
    "usgs": os.path.join(PATH, 'usgs_event.xml'),
    "focmec": os.path.join(PATH, 'quakeml_1.2_focalmechanism.xml'),
}


class QuakeMLIndexerTestCase(TestCase):

    def setUp(self):
        pass

    def test_indexing(self):
        expected_usgs = [
            {'agency': 'ci',
             'author': None,
             'depth_in_m': 10.0,
             'evaluation_mode': None,
             'event_type': 'quarry blast',
             'geometry': [Point(-117.6623333, 35.0476667)],
             'has_focal_mechanism': False,
             'has_moment_tensor': False,
             'latitude': 35.0476667,
             'longitude': -117.6623333,
             'magnitude': 1.54,
             'magnitude_type': 'ml',
             'origin_time': '2014-11-06T00:24:42.240000Z',
             'public': True,
             'quakeml_id': 'quakeml:comcat.cr.usgs.gov/fdsnws/event/1/'
                           'query?eventid=ci37285320&amp;format=quakeml'},
            {'agency': 'uw',
             'author': None,
             'depth_in_m': 0.0,
             'evaluation_mode': None,
             'event_type': 'quarry blast',
             'geometry': [Point(-120.2807, 42.138)],
             'has_focal_mechanism': False,
             'has_moment_tensor': False,
             'latitude': 42.138,
             'longitude': -120.2807,
             'magnitude': 1.6,
             'magnitude_type': 'Md',
             'origin_time': '2014-11-14T21:07:48.200000Z',
             'public': True,
             'quakeml_id': 'quakeml:comcat.cr.usgs.gov/fdsnws/event/1/'
                           'query?eventid=uw60916552&amp;format=quakeml'}]
        expected_focmec = [
            {'agency': None,
             'author': None,
             'depth_in_m': None,
             'evaluation_mode': None,
             'event_type': None,
             'geometry': None,
             'has_focal_mechanism': True,
             'has_moment_tensor': True,
             'latitude': None,
             'longitude': None,
             'magnitude': None,
             'magnitude_type': None,
             'origin_time': None,
             'public': True,
             'quakeml_id': 'smi:ISC/evid=11713537'}]
        indexer = QuakeMLIndexerPlugin()
        result_usgs = indexer.index(FILES['usgs'])
        result_focmec = indexer.index(FILES['focmec'])
        self.assertEqual(expected_usgs, result_usgs)
        self.assertEqual(expected_focmec, result_focmec)
