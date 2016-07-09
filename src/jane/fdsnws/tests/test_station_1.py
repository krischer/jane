# -*- coding: utf-8 -*-

import base64
import io
import tempfile
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
from jane.waveforms.process_waveforms import process_file


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

#     def test_query_nodata(self):
#         # not existing - error 204
#         param = '?start=2012-01-01&end=2012-01-02&net=GE&sta=APE&cha=EHE'
#         response = self.client.get('/fdsnws/station/1/query' + param)
#         self.assertEqual(response.status_code, 204)
#         self.assertTrue('Not Found: No data' in response.reason_phrase)
#         # not existing - error 404
#         param += '&nodata=404'
#         response = self.client.get('/fdsnws/station/1/query' + param)
#         self.assertEqual(response.status_code, 404)
#         self.assertTrue('Not Found: No data' in response.reason_phrase)
#
#     def test_query_data(self):
#         expected = read(FILES[0])[0]
#         params = {
#             'station': expected.meta.station,
#             'cha': expected.meta.channel,
#             'start': expected.meta.starttime,
#             'end': expected.meta.endtime
#         }
#         # 1 - query using HTTP GET
#         response = self.client.get('/fdsnws/station/1/query', params)
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('OK' in response.reason_phrase)
#         # compare streams
#         got = read(io.BytesIO(response.getvalue()))[0]
#         numpy.testing.assert_equal(got.data, expected.data)
#         self.assertEqual(got, expected)
#         # 2 - query using HTTP POST
#         response = self.client.post('/fdsnws/station/1/query', params)
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('OK' in response.reason_phrase)
#         # compare streams
#         got = read(io.BytesIO(response.getvalue()))[0]
#         numpy.testing.assert_equal(got.data, expected.data)
#         self.assertEqual(got, expected)
#
#     def test_queryauth_nodata(self):
#         param = '?start=2012-01-01&end=2012-01-02&net=GE&sta=APE&cha=EHE'
#
#         # 1 - no credentials - error 401
#         response = self.client.get('/fdsnws/station/1/queryauth' + param)
#         self.assertEqual(response.status_code, 401)
#
#         # 2 - invalid credentials - error 401
#         response = self.client.get('/fdsnws/station/1/queryauth' + param,
#                                    **self.invalid_auth_headers)
#         self.assertEqual(response.status_code, 401)
#
#         # 3 - valid credentials - not existing - error 204
#         response = self.client.get('/fdsnws/station/1/queryauth' + param,
#                                    **self.valid_auth_headers)
#         self.assertEqual(response.status_code, 204)
#         self.assertTrue('Not Found: No data' in response.reason_phrase)
#
#         # 4 - valid credentials - not existing - error 404
#         param += '&nodata=404'
#         response = self.client.get('/fdsnws/station/1/queryauth' + param,
#                                    **self.valid_auth_headers)
#         self.assertEqual(response.status_code, 404)
#         self.assertTrue('Not Found: No data' in response.reason_phrase)
#
#     def test_queryauth_data(self):
#         expected = read(FILES[0])[0]
#         params = {
#             'station': expected.meta.station,
#             'cha': expected.meta.channel,
#             'start': expected.meta.starttime,
#             'end': expected.meta.endtime,
#         }
#
#         # 1 - no credentials GET - error 401
#         response = self.client.get('/fdsnws/station/1/queryauth', params)
#         self.assertEqual(response.status_code, 401)
#
#         # 2 - invalid credentials GET - error 401
#         response = self.client.get('/fdsnws/station/1/queryauth', params,
#                                    **self.invalid_auth_headers)
#         self.assertEqual(response.status_code, 401)
#
#         # 3 - no credentials POST - error 401
#         response = self.client.post('/fdsnws/station/1/queryauth', params)
#         self.assertEqual(response.status_code, 401)
#
#         # 4 - invalid credentials POST - error 401
#         response = self.client.post('/fdsnws/station/1/queryauth', params,
#                                     **self.invalid_auth_headers)
#         self.assertEqual(response.status_code, 401)
#
#         # 5 - query using HTTP GET
#         response = self.client.get('/fdsnws/station/1/queryauth', params,
#                                    **self.valid_auth_headers)
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('OK' in response.reason_phrase)
#
#         # compare streams
#         got = read(io.BytesIO(response.getvalue()))[0]
#         numpy.testing.assert_equal(got.data, expected.data)
#         self.assertEqual(got, expected)
#
#         # 6 - query using HTTP POST
#         response = self.client.post('/fdsnws/station/1/queryauth', params,
#                                     **self.valid_auth_headers)
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('OK' in response.reason_phrase)
#
#         # compare streams
#         got = read(io.BytesIO(response.getvalue()))[0]
#         numpy.testing.assert_equal(got.data, expected.data)
#         self.assertEqual(got, expected)
#
#     def test_query_data_wildcards(self):
#         # query using wildcards
#         param = '?endtime=2010-03-25T00:00:30&network=TA&channel=BH%2A' + \
#             '&starttime=2010-03-25&station=A25A'
#         response = self.client.get('/fdsnws/station/1/query' + param)
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('OK' in response.reason_phrase)
#
#     def test_restrictions(self):
#         """
#         Tests if the waveform restrictions actually work as expected.
#         """
#         params = {
#             'station': 'A25A',
#             'cha': 'BHE',
#             'start': '2010-03-25T00:00:00',
#             'end': '2010-03-26T00:00:00'
#         }
#
#         # No restrictions currently apply - we should get something.
#         response = self.client.get('/fdsnws/station/1/query', params)
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('OK' in response.reason_phrase)
#         st = read(io.BytesIO(response.getvalue()))
#         self.assertEqual(len(st), 1)
#         self.assertEqual(st[0].id, "TA.A25A..BHE")
#
#         # Now add restrictions to this one station.
#         # create anonymous user
#         r = Restriction.objects.get_or_create(network="TA", station="A25A")[0]
#         r.users.add(User.objects.filter(username='random')[0])
#         r.save()
#
#         # Now the same query should no longer return something as the
#         # station has been restricted.
#         response = self.client.get('/fdsnws/station/1/query', params)
#         self.assertEqual(response.status_code, 204)
#
#         # RJOB data can still be retrieved.
#         params["station"] = "RJOB"
#         params["cha"] = "Z"
#         params["start"] = "2005-01-01T00:00:00"
#         response = self.client.get('/fdsnws/station/1/query', params)
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue('OK' in response.reason_phrase)
#         st = read(io.BytesIO(response.getvalue()))
#         self.assertEqual(len(st), 1)
#         self.assertEqual(st[0].id, ".RJOB..Z")
#
#

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

#
#     def test_query_data(self):
#         # query using ObsPy
#         t1 = UTCDateTime("2005-10-06T07:21:59.850000")
#         t2 = UTCDateTime("2005-10-06T07:24:59.845000")
#         client = FDSNClient(self.live_server_url)
#         got = client.get_waveforms("", "RJOB", "", "Z", t1, t2)[0]
#         expected = read(FILES[0])[0]
#         numpy.testing.assert_equal(got.data, expected.data)
#         self.assertEqual(got, expected)
#
#     def test_query_data_wildcards(self):
#         # query using wildcards
#         t = UTCDateTime(2010, 3, 25, 0, 0)
#         client = FDSNClient(self.live_server_url)
#         # 1
#         st = client.get_waveforms("TA", "A25A", "", "BHZ", t, t + 30)
#         self.assertEqual(len(st), 1)
#         self.assertEqual(len(st[0].data), 1201)
#         self.assertEqual(st[0].id, 'TA.A25A..BHZ')
#         # 2
#         st = client.get_waveforms("TA", "A25A", "", "BHZ,BHN,BHE", t, t + 30)
#         self.assertEqual(len(st), 3)
#         # 3
#         st = client.get_waveforms("TA", "A25A", "", "BH*", t, t + 30)
#         self.assertEqual(len(st), 3)
#         # 4
#         st = client.get_waveforms("TA", "A25A", "", "BH?", t, t + 30)
#         self.assertEqual(len(st), 3)
#         # 5
#         st = client.get_waveforms("TA", "A25A", "", "BH?,VCO", t, t + 30)
#         self.assertEqual(len(st), 4)
#         # 6
#         st = client.get_waveforms("TA", "A25A", "", "BH?,-BHZ", t, t + 30)
#         self.assertEqual(len(st), 2)
#         # 7
#         st = client.get_waveforms("TA", "A25A", "", "*", t, t + 30)
#         self.assertEqual(len(st), 19)  # xxx: why 19 - should be 22!
#         st = client.get_waveforms("TA", "A25A", "", "*,-BHZ", t, t + 30)
#         self.assertEqual(len(st), 18)
