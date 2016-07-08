# -*- coding: utf-8 -*-

import base64
import os

import django
from django.contrib.auth.models import User, Permission
from django.contrib.auth.hashers import make_password
from django.test import TestCase

from jane.documents.plugins import initialize_plugins


django.setup()


PATH = os.path.join(os.path.dirname(__file__), 'data')
FILES = {
    "bw.altm": os.path.join(PATH, 'BW.ALTM.xml')
}


class StationXMLPluginTestCase(TestCase):
    """
    Tests for the StationXML plugin.
    """
    def setUp(self):
        # The test case class somehow messes with the plugins - thus we have
        # to initialize them all the time.
        initialize_plugins()

        self.user = User.objects.get_or_create(
            username='random', password=make_password('random'))[0]

        self.can_modify_stationxml_permission = \
            Permission.objects.filter(codename='can_modify_stationxml').first()

        credentials = base64.b64encode(b'random:random')
        self.valid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

    def test_uploading(self):
        self.user.user_permissions.add(self.can_modify_stationxml_permission)
        with open(FILES["bw.altm"], "rb") as fh:
            r = self.client.put("/rest/documents/stationxml/BW.ALTM.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        r = self.client.get("/rest/document_indices/stationxml").json()
        self.assertEqual(len(r["results"]), 3)

        self.assertEqual(r["results"][0]["data_content_type"], "text/xml")

        self.assertEqual(r["results"][0]["indexed_data"], {
            'azimuth': 0.0,
            'channel': 'EHZ',
            'depth_in_m': 0.0,
            'dip': -90.0,
            'elevation_in_m': 430.0,
            'end_date': None,
            'latitude': 48.995167,
            'location': '',
            'longitude': 11.519922,
            'network': 'BW',
            'network_name': 'BayernNetz',
            'sample_rate': 200.0,
            'sensitivity_frequency': 2.0,
            'sensor_type': 'Lennartz LE-3D/1 seismometer',
            'start_date': '2010-04-29T00:00:00.000000Z',
            'station': 'ALTM',
            'station_creation_date': '2010-04-29T00:00:00.000000Z',
            'station_name': 'Beilngries, Bavaria, BW-Net',
            'total_sensitivity': 251650000.0,
            'units_after_sensitivity': 'M/S'})

        self.assertEqual(r["results"][1]["indexed_data"], {
            'azimuth': 0.0,
            'channel': 'EHN',
            'depth_in_m': 0.0,
            'dip': 0.0,
            'elevation_in_m': 430.0,
            'end_date': None,
            'latitude': 48.995167,
            'location': '',
            'longitude': 11.519922,
            'network': 'BW',
            'network_name': 'BayernNetz',
            'sample_rate': 200.0,
            'sensitivity_frequency': 2.0,
            'sensor_type': 'Lennartz LE-3D/1 seismometer',
            'start_date': '2010-04-29T00:00:00.000000Z',
            'station': 'ALTM',
            'station_creation_date': '2010-04-29T00:00:00.000000Z',
            'station_name': 'Beilngries, Bavaria, BW-Net',
            'total_sensitivity': 251650000.0,
            'units_after_sensitivity': 'M/S'})

        self.assertEqual(r["results"][2]["indexed_data"], {
            'azimuth': 90.0,
            'channel': 'EHE',
            'depth_in_m': 0.0,
            'dip': 0.0,
            'elevation_in_m': 430.0,
            'end_date': None,
            'latitude': 48.995167,
            'location': '',
            'longitude': 11.519922,
            'network': 'BW',
            'network_name': 'BayernNetz',
            'sample_rate': 200.0,
            'sensitivity_frequency': 2.0,
            'sensor_type': 'Lennartz LE-3D/1 seismometer',
            'start_date': '2010-04-29T00:00:00.000000Z',
            'station': 'ALTM',
            'station_creation_date': '2010-04-29T00:00:00.000000Z',
            'station_name': 'Beilngries, Bavaria, BW-Net',
            'total_sensitivity': 251650000.0,
            'units_after_sensitivity': 'M/S'})

        # Everything should also have an attachment!
        self.assertEqual(r["results"][0]["attachments_count"], 1)
        self.assertEqual(r["results"][1]["attachments_count"], 1)
        self.assertEqual(r["results"][2]["attachments_count"], 1)

        # Get the attachment and make sure it is a picture.
        r = self.client.get(r["results"][0]["attachments_url"])
        r = r.json()["results"]
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["content_type"], "image/png")
        self.assertEqual(r[0]["category"], "response")
        # Just make sure it at least returns something.
        attachment_data = self.client.get(r[0]["data_url"]).content
        self.assertTrue(len(attachment_data) > 100)
