# -*- coding: utf-8 -*-

import base64
import os

import django
from django.contrib.auth.models import User, Permission
from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos.point import Point
from django.test import TestCase

from jane.quakeml.plugins import QuakeMLIndexerPlugin
from jane.documents.plugins import initialize_plugins


django.setup()


PATH = os.path.join(os.path.dirname(__file__), 'data')
FILES = {
    "usgs": os.path.join(PATH, 'usgs_event.xml'),
    "focmec": os.path.join(PATH, 'quakeml_1.2_focalmechanism.xml'),
    "private": os.path.join(PATH, "private_event.xml")
}


class QuakeMLPluginTestCase(TestCase):
    def setUp(self):

        # The test case class somehow messes with the plugins - thus we have
        # to initialize them all the time.
        initialize_plugins()

        self.user = User.objects.get_or_create(
            username='random', password=make_password('random'))[0]

        self.can_modify_quakeml_permission = \
            Permission.objects.filter(codename='can_modify_quakeml').first()

        credentials = base64.b64encode(b'random:random')
        self.valid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

        credentials = base64.b64encode(b'random:random2')
        self.invalid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

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

    def test_quakeml_uploading(self):
        """
        Also a bit of an integration test for the plugin system which
        actually requires a plugin to be fully tested.
        """
        path = "/rest/document_indices/quakeml"
        # Nothing there yet.
        events = self.client.get(path).json()["results"]
        self.assertEqual(len(events), 0)

        with open(FILES["focmec"], "rb") as fh:
            data = fh.read()

        # Unauthorized - thus cannot upload events.
        r = self.client.put("/rest/documents/quakeml/quake.xml", data=data)
        self.assertEqual(r.status_code, 401)
        events = self.client.get(path).json()["results"]
        self.assertEqual(len(events), 0)

        # Now authorize but with invalid credentials.
        r = self.client.put("/rest/documents/quakeml/quake.xml", data=data,
                            **self.invalid_auth_headers)
        self.assertEqual(r.status_code, 401)
        events = self.client.get(path).json()["results"]
        self.assertEqual(len(events), 0)

        # Valid credentials but not the right permissions.
        r = self.client.put("/rest/documents/quakeml/quake.xml", data=data,
                            **self.valid_auth_headers)
        self.assertEqual(r.status_code, 401)
        events = self.client.get(path).json()["results"]
        self.assertEqual(len(events), 0)

        # Add the proper permissions. Now it should work.
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        r = self.client.put("/rest/documents/quakeml/quake.xml", data=data,
                            **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        events = self.client.get(path).json()["results"]
        self.assertEqual(len(events), 1)
        # And it should have also resulted in a single document being uploaded.
        documents = \
            self.client.get("/rest/documents/quakeml").json()["results"]
        self.assertEqual(len(documents), 1)

    def test_can_see_private_event_permission_plugin(self):
        """
        Tests the can see private events permission plugin by using the REST
        interface.
        """
        self.user.user_permissions.add(self.can_modify_quakeml_permission)

        # Upload private event.
        with open(FILES["private"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)

        # By default nobody can see it. First unauthorized.
        path = "/rest/document_indices/quakeml"
        self.assertEqual(len(self.client.get(path).json()["results"]), 0)

        # Authorized but missing permissions.
        self.assertEqual(len(self.client.get(
            path, **self.valid_auth_headers).json()["results"]), 0)

        # Add the required permission.
        p = Permission.objects.filter(codename="can_see_private_events")\
            .first()
        self.user.user_permissions.add(p)
        # Now it works.
        self.assertEqual(len(self.client.get(
            path, **self.valid_auth_headers).json()["results"]), 1)
