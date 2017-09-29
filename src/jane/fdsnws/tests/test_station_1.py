# -*- coding: utf-8 -*-

import base64
import io
import os
from unittest import mock

import django
from django.contrib.auth.models import User, Permission
from django.contrib.auth.hashers import make_password
from django.test import TestCase, LiveServerTestCase

import obspy
from obspy.clients.fdsn import Client as FDSNClient
from obspy.clients.fdsn.header import FDSNException
from obspy.io.stationxml.core import validate_stationxml


from jane.documents.models import Document
from jane.documents.plugins import initialize_plugins
from jane.waveforms.models import Restriction


django.setup()


PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    __file__))), "stationxml", "tests", "data")
FILES = {
    "BW.ALTM.xml": os.path.join(PATH, "BW.ALTM.xml")
}


class Station1TestCase(TestCase):

    def setUp(self):
        # The test case class somehow messes with the plugins - thus we have
        # to initialize them all the time.
        initialize_plugins()

        self.user = User.objects.get_or_create(
            username='random', password=make_password('random'))[0]
        self.user.user_permissions.add(Permission.objects.filter(
            codename='can_modify_stationxml').first())

        credentials = base64.b64encode(b'random:random')
        self.valid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

        credentials = base64.b64encode(b'random:random2')
        self.invalid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

        # Test will then execute much faster.
        with mock.patch("obspy.core.inventory.channel.Channel.plot"):
            with open(FILES["BW.ALTM.xml"], "rb") as fh:
                Document.objects.add_or_modify_document(
                    document_type="stationxml",
                    name="station.xml",
                    data=fh.read(),
                    user=self.user)

    def test_version(self):
        # 1 - HTTP OK
        response = self.client.get('/fdsnws/station/1/version')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertEqual(response.content, b'1.1.1')
        # 2 - incorrect trailing slash will work too
        response = self.client.get('/fdsnws/station/1/version/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertEqual(response.content, b'1.1.1')

    def test_wadl(self):
        # 1 - HTTP OK
        response = self.client.get('/fdsnws/station/1/application.wadl')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'],
                         'application/xml; charset=utf-8')
        self.assertTrue(response.content.startswith(b'<?xml'))
        # 2 - incorrect trailing slash will work too
        response = self.client.get('/fdsnws/station/1/application.wadl/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'],
                         'application/xml; charset=utf-8')
        self.assertTrue(response.content.startswith(b'<?xml'))

    def test_index(self):
        # 1 - redirect if APPEND_SLASH = True
        response = self.client.get('/fdsnws/station/1')
        self.assertEqual(response.status_code, 301)
        # 2 - HTTP OK
        response = self.client.get('/fdsnws/station/1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'text/html; charset=utf-8')

    def test_stationxml_is_valid(self):
        """
        Make sure the generated stationxml files are actually valid.
        """
        with io.BytesIO() as buf:
            buf.write(self.client.get(
                "/fdsnws/station/1/query?level=network").content)
            buf.seek(0, 0)
            self.assertTrue(validate_stationxml(buf)[0])

        with io.BytesIO() as buf:
            buf.write(self.client.get(
                "/fdsnws/station/1/query?level=station").content)
            buf.seek(0, 0)
            self.assertTrue(validate_stationxml(buf)[0])

        with io.BytesIO() as buf:
            buf.write(self.client.get(
                "/fdsnws/station/1/query?level=channel").content)
            buf.seek(0, 0)
            self.assertTrue(validate_stationxml(buf)[0])

        with io.BytesIO() as buf:
            buf.write(self.client.get(
                "/fdsnws/station/1/query?level=response").content)
            buf.seek(0, 0)
            self.assertTrue(validate_stationxml(buf)[0])

    @mock.patch("jane.fdsnws.views.station_1.query_stations")
    def test_shorthand_and_longhand_parameters_versions(self, p):
        """
        Just use a mock and check the arguments passed to station query method.
        """
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?starttime=1991-1-1')
        self.assertEqual(p.call_args_list[0][1]["starttime"],
                         662688000.0)
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?start=1991-1-1')
        self.assertEqual(p.call_args_list[0][1]["starttime"],
                         662688000.0)

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?endtime=1991-1-1')
        self.assertEqual(p.call_args_list[0][1]["endtime"], 662688000.0)
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?end=1991-1-1')
        self.assertEqual(p.call_args_list[0][1]["endtime"], 662688000.0)

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?network=BW')
        self.assertEqual(p.call_args_list[0][1]["network"], ["BW"])
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?net=BW')
        self.assertEqual(p.call_args_list[0][1]["network"], ["BW"])

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?station=ALTM')
        self.assertEqual(p.call_args_list[0][1]["station"], ["ALTM"])
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?sta=ALTM')
        self.assertEqual(p.call_args_list[0][1]["station"], ["ALTM"])

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?location=00')
        self.assertEqual(p.call_args_list[0][1]["location"], ["00"])
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?loc=00')
        self.assertEqual(p.call_args_list[0][1]["location"], ["00"])

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?channel=BHE')
        self.assertEqual(p.call_args_list[0][1]["channel"], ["BHE"])
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?cha=BHE')
        self.assertEqual(p.call_args_list[0][1]["channel"], ["BHE"])

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?minlatitude=10.0')
        self.assertEqual(p.call_args_list[0][1]["minlatitude"], 10.0)
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?minlat=10.0')
        self.assertEqual(p.call_args_list[0][1]["minlatitude"], 10.0)

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?maxlatitude=10.0')
        self.assertEqual(p.call_args_list[0][1]["maxlatitude"], 10.0)
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?maxlat=10.0')
        self.assertEqual(p.call_args_list[0][1]["maxlatitude"], 10.0)

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?minlongitude=10.0')
        self.assertEqual(p.call_args_list[0][1]["minlongitude"], 10.0)
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?minlon=10.0')
        self.assertEqual(p.call_args_list[0][1]["minlongitude"], 10.0)

        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?maxlongitude=10.0')
        self.assertEqual(p.call_args_list[0][1]["maxlongitude"], 10.0)
        p.reset_mock()
        with self.assertRaises(Exception):
            self.client.get(
                '/fdsnws/station/1/query?maxlon=10.0')
        self.assertEqual(p.call_args_list[0][1]["maxlongitude"], 10.0)

    def test_query_nodata(self):
        # not existing - error 204
        response = self.client.get('/fdsnws/station/1/query?net=BB')
        self.assertEqual(response.status_code, 204)
        self.assertTrue('Not Found: No data' in response.reason_phrase)

        # not existing - error 404
        response = self.client.get('/fdsnws/station/1/query?net=BB&nodata=404')
        self.assertEqual(response.status_code, 404)
        self.assertTrue('Not Found: No data' in response.reason_phrase)

    def test_text_format(self):
        d = self.client.get(
            '/fdsnws/station/1/query?format=text&level=network').content
        self.assertEqual(
            d.decode(),
            "#Network|Description|StartTime|EndTime|TotalStations\n"
            "BW|BayernNetz|2010-04-29T00:00:00.000000Z||1\n"
        )
        self.assertTrue(d.decode().startswith("#Network|Description"))

        d = self.client.get(
            '/fdsnws/station/1/query?format=text&level=station').content
        self.assertEqual(
            d.decode(),
            '#Network|Station|Latitude|Longitude|Elevation|SiteName|'
            'StartTime|EndTime\n'
            'BW|ALTM|48.995167|11.519922|430.0'
            '|Beilngries, Bavaria, BW-Net|2010-04-29T00:00:00.000000Z|\n'
        )
        self.assertTrue(d.decode().startswith("#Network|Station|Latitude"))

        d = self.client.get(
            '/fdsnws/station/1/query?format=text&level=channel').content
        self.assertEqual(
            d.decode(),
            "#Network|Station|Location|Channel|Latitude|Longitude|Elevation"
            "|Depth|Azimuth|Dip|SensorDescription|Scale|ScaleFreq|ScaleUnits"
            "|SampleRate|StartTime|EndTime\n"
            "BW|ALTM||EHZ|48.995167|11.519922"
            "|430.0|0.0|0.0|-90.0|Lennartz LE-3D/1 "
            "seismometer|251650000.0|2.0|M/S|200.0|2010-04-29T00:00:00"
            ".000000Z|2011-01-01T00:00:00.000000Z\n"
            "BW|ALTM||EHN|48.995167|11"
            ".519922|430.0|0.0|0.0|0.0|Lennartz LE-3D/1 "
            "seismometer|251650000.0|2.0|M/S|200.0|2010-04-29T00:00:00"
            ".000000Z|\n"
            "BW|ALTM||EHE|48.995167|11.519922|430.0|0.0|90.0|0.0"
            "|Lennartz LE-3D/1 "
            "seismometer|251650000.0|2.0|M/S|200.0|2010-04-29T00:00:00"
            ".000000Z|\n"
        )

    def test_query_auth_data(self):
        """
        Just a copy of the text test but using queryauth.
        """
        d = self.client.get(
            '/fdsnws/station/1/queryauth?format=text&level=network',
            **self.valid_auth_headers).content
        self.assertEqual(
            d.decode(),
            "#Network|Description|StartTime|EndTime|TotalStations\n"
            "BW|BayernNetz|2010-04-29T00:00:00.000000Z||1\n"
        )
        self.assertTrue(d.decode().startswith("#Network|Description"))

        d = self.client.get(
            '/fdsnws/station/1/queryauth?format=text&level=station',
            **self.valid_auth_headers).content
        self.assertEqual(
            d.decode(),
            '#Network|Station|Latitude|Longitude|Elevation|SiteName|'
            'StartTime|EndTime\n'
            'BW|ALTM|48.995167|11.519922|430.0'
            '|Beilngries, Bavaria, BW-Net|2010-04-29T00:00:00.000000Z|\n'
        )
        self.assertTrue(d.decode().startswith("#Network|Station|Latitude"))

        d = self.client.get(
            '/fdsnws/station/1/queryauth?format=text&level=channel',
            **self.valid_auth_headers).content
        self.assertEqual(
            d.decode(),
            "#Network|Station|Location|Channel|Latitude|Longitude|Elevation"
            "|Depth|Azimuth|Dip|SensorDescription|Scale|ScaleFreq|ScaleUnits"
            "|SampleRate|StartTime|EndTime\n"
            "BW|ALTM||EHZ|48.995167|11.519922"
            "|430.0|0.0|0.0|-90.0|Lennartz LE-3D/1 "
            "seismometer|251650000.0|2.0|M/S|200.0|2010-04-29T00:00:00"
            ".000000Z|2011-01-01T00:00:00.000000Z\n"
            "BW|ALTM||EHN|48.995167|11"
            ".519922|430.0|0.0|0.0|0.0|Lennartz LE-3D/1 "
            "seismometer|251650000.0|2.0|M/S|200.0|2010-04-29T00:00:00"
            ".000000Z|\n"
            "BW|ALTM||EHE|48.995167|11.519922|430.0|0.0|90.0|0.0"
            "|Lennartz LE-3D/1 "
            "seismometer|251650000.0|2.0|M/S|200.0|2010-04-29T00:00:00"
            ".000000Z|\n"
        )

    def test_queryauth_nodata(self):
        param = '?network=BB'

        # 1 - no credentials - error 401
        response = self.client.get('/fdsnws/station/1/queryauth' + param)
        self.assertEqual(response.status_code, 401)

        # 2 - invalid credentials - error 401
        response = self.client.get('/fdsnws/station/1/queryauth' + param,
                                   **self.invalid_auth_headers)
        self.assertEqual(response.status_code, 401)

        # 3 - valid credentials - not existing - error 204
        response = self.client.get('/fdsnws/station/1/queryauth' + param,
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 204)
        self.assertTrue('Not Found: No data' in response.reason_phrase)

        # 4 - valid credentials - not existing - error 404
        param += '&nodata=404'
        response = self.client.get('/fdsnws/station/1/queryauth' + param,
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 404)
        self.assertTrue('Not Found: No data' in response.reason_phrase)

    def test_restrictions(self):
        """
        Tests if the waveform restrictions actually work as expected.
        """
        # No restrictions currently apply - we should get something.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # First add a restriction that does nothing.
        r = Restriction.objects.get_or_create(network="AA", station="BBBB")[0]
        r.users.add(User.objects.filter(username='random')[0])
        r.save()
        # Everything should still work.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # Now add restrictions that does something.
        r = Restriction.objects.get_or_create(network="BW", station="ALTM")[0]
        r.users.add(User.objects.filter(username='random')[0])
        r.save()

        # Now the same query should no longer return something as the
        # station has been restricted.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 204)

        # The correct user can still get the stations.
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # Make another user that has not been added to this restriction - he
        # should not be able to retrieve it.
        self.client.logout()
        User.objects.get_or_create(
            username='some_dude', password=make_password('some_dude'))[0]
        credentials = base64.b64encode(b'some_dude:some_dude')
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **auth_headers)
        self.assertEqual(response.status_code, 204)

    def test_restrictions_asterisk_network_and_station(self):
        """
        Tests if the waveform restrictions actually work as expected.
        """
        # No restrictions currently apply - we should get something.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # add restriction on all stations
        r = Restriction.objects.get_or_create(network="*", station="*")[0]
        r.users.add(User.objects.filter(username='random')[0])
        r.save()

        # Now the same query should no longer return something as the
        # station has been restricted.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 204)

        # The correct user can still get the stations.
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # Make another user that has not been added to this restriction - he
        # should not be able to retrieve it.
        self.client.logout()
        User.objects.get_or_create(
            username='some_dude', password=make_password('some_dude'))[0]
        credentials = base64.b64encode(b'some_dude:some_dude')
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **auth_headers)
        self.assertEqual(response.status_code, 204)

    def test_restrictions_asterisk_network(self):
        """
        Tests if the waveform restrictions actually work as expected.
        """
        # No restrictions currently apply - we should get something.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # add restriction on ALTM stations
        r = Restriction.objects.get_or_create(network="*", station="ALTM")[0]
        r.users.add(User.objects.filter(username='random')[0])
        r.save()

        # Now the same query should no longer return something as the
        # station has been restricted.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 204)

        # The correct user can still get the stations.
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # Make another user that has not been added to this restriction - he
        # should not be able to retrieve it.
        self.client.logout()
        User.objects.get_or_create(
            username='some_dude', password=make_password('some_dude'))[0]
        credentials = base64.b64encode(b'some_dude:some_dude')
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **auth_headers)
        self.assertEqual(response.status_code, 204)

    def test_restrictions_asterisk_station(self):
        """
        Tests if the waveform restrictions actually work as expected.
        """
        # No restrictions currently apply - we should get something.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # add restriction on all BW-network stations
        r = Restriction.objects.get_or_create(network="BW", station="*")[0]
        r.users.add(User.objects.filter(username='random')[0])
        r.save()

        # Now the same query should no longer return something as the
        # station has been restricted.
        response = self.client.get('/fdsnws/station/1/query')
        self.assertEqual(response.status_code, 204)

        # The correct user can still get the stations.
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        inv = obspy.read_inventory(io.BytesIO(response.getvalue()))
        self.assertEqual(inv.get_contents()["stations"],
                         ["BW.ALTM (Beilngries, Bavaria, BW-Net)"])

        # Make another user that has not been added to this restriction - he
        # should not be able to retrieve it.
        self.client.logout()
        User.objects.get_or_create(
            username='some_dude', password=make_password('some_dude'))[0]
        credentials = base64.b64encode(b'some_dude:some_dude')
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }
        response = self.client.get('/fdsnws/station/1/queryauth',
                                   **auth_headers)
        self.assertEqual(response.status_code, 204)


class Station1LiveServerTestCase(LiveServerTestCase):
    """
    Launches a live Django server in the background on setup, and shuts it down
    on teardown. This allows the use of automated test clients other than the
    Django dummy client such as obspy.clients.fdsn.Client.
    """
    def setUp(self):
        # The test case class somehow messes with the plugins - thus we have
        # to initialize them all the time.
        initialize_plugins()

        self.user = User.objects.get_or_create(
            username='random', password=make_password('random'))[0]
        self.user.user_permissions.add(Permission.objects.filter(
            codename='can_modify_stationxml').first())

        credentials = base64.b64encode(b'random:random')
        self.valid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

        credentials = base64.b64encode(b'random:random2')
        self.invalid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

        # Mocking makes the plotting fails which is the slow operation -
        # thus the tests execute much faster.
        with mock.patch("obspy.core.inventory.channel.Channel.plot"):
            # Add a station.
            with open(FILES["BW.ALTM.xml"], "rb") as fh:
                Document.objects.add_or_modify_document(
                    document_type="stationxml",
                    name="station.xml",
                    data=fh.read(),
                    user=self.user)

    def test_level_argument(self):
        client = FDSNClient(self.live_server_url)

        inv = client.get_stations(level="channel")
        c = inv.get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)

        inv = client.get_stations(level="station")
        c = inv.get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 0)

        inv = client.get_stations(level="network")
        c = inv.get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 0)
        self.assertEqual(len(c["channels"]), 0)

        inv = client.get_stations(level="response")
        c = inv.get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)

        for channel in inv[0][0]:
            self.assertIsNotNone(channel.response)

    def test_temporal_queries(self):
        """
        Test the various temporal parameters.
        """
        # All 3 channels start at the same time, two are open ended,
        # one ends a bit earlier.
        client = FDSNClient(self.live_server_url)

        start = obspy.UTCDateTime("2010-04-29T00:00:00.000000Z")
        end = obspy.UTCDateTime("2011-01-01T00:00:00.000000Z")

        inv = client.get_stations(starttime=obspy.UTCDateTime(2000, 1, 1),
                                  level="channel")
        c = inv.get_contents()
        self.assertEqual(c["channels"],
                         ['BW.ALTM..EHE', 'BW.ALTM..EHN', 'BW.ALTM..EHZ'])
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)

        # Same thing.
        c = client.get_stations(starttime=start - 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)

        # Go before and after the endtime of the one channel.
        c = client.get_stations(starttime=end - 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)
        c = client.get_stations(starttime=end + 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 2)

        # Test the endtime parameter.
        inv = client.get_stations(endtime=obspy.UTCDateTime(2016, 1, 1),
                                  level="channel")
        c = inv.get_contents()
        self.assertEqual(c["channels"],
                         ['BW.ALTM..EHE', 'BW.ALTM..EHN', 'BW.ALTM..EHZ'])
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)
        c = client.get_stations(endtime=start + 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)
        with self.assertRaises(FDSNException):
            client.get_stations(endtime=start - 10, level="channel")

        # startbefore
        c = client.get_stations(startbefore=start + 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)
        with self.assertRaises(FDSNException):
            client.get_stations(startbefore=start - 10, level="channel")

        # startafter
        c = client.get_stations(startafter=start - 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)
        with self.assertRaises(FDSNException):
            client.get_stations(startafter=start + 10, level="channel")

        # endbefore
        c = client.get_stations(endbefore=end + 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 1)
        with self.assertRaises(FDSNException):
            client.get_stations(endbefore=end - 10, level="channel")

        # endafter
        c = client.get_stations(endafter=end - 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 3)
        c = client.get_stations(endafter=end + 10,
                                level="channel").get_contents()
        self.assertEqual(len(c["networks"]), 1)
        self.assertEqual(len(c["stations"]), 1)
        self.assertEqual(len(c["channels"]), 2)

    def test_total_and_selected_number_of_sta_and_cha(self):
        client = FDSNClient(self.live_server_url)

        inv = client.get_stations(level="network")
        self.assertEqual(inv[0].total_number_of_stations, 1)
        self.assertEqual(inv[0].selected_number_of_stations, 0)

        inv = client.get_stations(level="station")
        self.assertEqual(inv[0].total_number_of_stations, 1)
        self.assertEqual(inv[0].selected_number_of_stations, 1)
        self.assertEqual(inv[0][0].total_number_of_channels, 3)
        self.assertEqual(inv[0][0].selected_number_of_channels, 0)

        inv = client.get_stations(level="channel")
        self.assertEqual(inv[0].total_number_of_stations, 1)
        self.assertEqual(inv[0].selected_number_of_stations, 1)
        self.assertEqual(inv[0][0].total_number_of_channels, 3)
        self.assertEqual(inv[0][0].selected_number_of_channels, 3)

        inv = client.get_stations(level="response")
        self.assertEqual(inv[0].total_number_of_stations, 1)
        self.assertEqual(inv[0].selected_number_of_stations, 1)
        self.assertEqual(inv[0][0].total_number_of_channels, 3)
        self.assertEqual(inv[0][0].selected_number_of_channels, 3)

    def test_seed_code_queries(self):
        client = FDSNClient(self.live_server_url)

        # First test some very specific queries.
        inv = client.get_stations(level="channel", network="BW",
                                  station="ALTM", location="--", channel="EH?")
        c = inv.get_contents()
        self.assertEqual(c["channels"],
                         ['BW.ALTM..EHE', 'BW.ALTM..EHN', 'BW.ALTM..EHZ'])

        client = FDSNClient(self.live_server_url)
        inv = client.get_stations(level="channel", network="BW",
                                  station="ALTM", location="--", channel="EH*")
        c = inv.get_contents()
        self.assertEqual(c["channels"],
                         ['BW.ALTM..EHE', 'BW.ALTM..EHN', 'BW.ALTM..EHZ'])

        client = FDSNClient(self.live_server_url)
        inv = client.get_stations(level="channel", network="BW",
                                  station="ALTM", location="", channel="EH*")
        c = inv.get_contents()
        self.assertEqual(c["channels"],
                         ['BW.ALTM..EHE', 'BW.ALTM..EHN', 'BW.ALTM..EHZ'])

        client = FDSNClient(self.live_server_url)
        inv = client.get_stations(level="channel", network="B*",
                                  station="AL?M", location="*", channel="EH*")
        c = inv.get_contents()
        self.assertEqual(c["channels"],
                         ['BW.ALTM..EHE', 'BW.ALTM..EHN', 'BW.ALTM..EHZ'])

        # Test exclusions. - First exclude things that don't exist in the
        # test database - should naturally still return everything.
        inv = client.get_stations(level="channel", network="-XX",
                                  station="-YY", location="-ZZ",
                                  channel="-BHE")
        c = inv.get_contents()
        self.assertEqual(c["channels"],
                         ['BW.ALTM..EHE', 'BW.ALTM..EHN', 'BW.ALTM..EHZ'])

        inv = client.get_stations(level="channel", channel="-EHE")
        c = inv.get_contents()
        self.assertEqual(c["channels"], ['BW.ALTM..EHN', 'BW.ALTM..EHZ'])

        inv = client.get_stations(level="channel", channel="-EHE,-EHN")
        c = inv.get_contents()
        self.assertEqual(c["channels"], ['BW.ALTM..EHZ'])

        # A couple of no-datas
        with self.assertRaises(FDSNException):
            client.get_stations(network="TA", station="ALTM",
                                location="--", channel="EH?")

        with self.assertRaises(FDSNException):
            client.get_stations(network="BW", station="FURT",
                                location="--", channel="EH?")

        with self.assertRaises(FDSNException):
            client.get_stations(network="BW", station="ALTM",
                                location="00", channel="EH?")

        with self.assertRaises(FDSNException):
            client.get_stations(network="BW", station="ALTM",
                                location="--", channel="BHZ?")

    def test_rectangular_geo_queries(self):
        client = FDSNClient(self.live_server_url)
        # lat = 48.995167
        # lon = 11.519922

        # This works.
        self.assertEqual(
            len(client.get_stations(
                minlatitude=48, maxlatitude=49,
                minlongitude=11, maxlongitude=12).get_contents()["stations"]),
            1)

        # Make sure one border does not include the point at a time.
        with self.assertRaises(FDSNException):
            client.get_stations(minlatitude=48.996, maxlatitude=49,
                                minlongitude=11, maxlongitude=12)

        with self.assertRaises(FDSNException):
            client.get_stations(minlatitude=48, maxlatitude=48.5,
                                minlongitude=11, maxlongitude=12)

        with self.assertRaises(FDSNException):
            client.get_stations(minlatitude=48, maxlatitude=49,
                                minlongitude=11.6, maxlongitude=12)

        with self.assertRaises(FDSNException):
            client.get_stations(minlatitude=48, maxlatitude=49,
                                minlongitude=11, maxlongitude=11.4)

    def test_radial_queries(self):
        client = FDSNClient(self.live_server_url)
        lat = 48.995167 + 1.0
        lon = 11.519922

        self.assertEqual(
            len(client.get_stations(
                latitude=lat, longitude=lon,
                maxradius=2).get_contents()["stations"]),
            1)

        self.assertEqual(
            len(client.get_stations(
                latitude=lat, longitude=lon,
                maxradius=1.1).get_contents()["stations"]),
            1)

        with self.assertRaises(FDSNException):
            client.get_stations(latitude=lat, longitude=lon,
                                minradius=1.1, maxradius=10)

        with self.assertRaises(FDSNException):
            client.get_stations(latitude=lat, longitude=lon,
                                minradius=0.1, maxradius=0.5)
