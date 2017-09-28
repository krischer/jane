# -*- coding: utf-8 -*-

import base64
import os

import django
from django.contrib.auth.models import User, Permission
from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import Point, LineString, MultiLineString
from django.test import TestCase

from jane.quakeml.plugins import QuakeMLIndexerPlugin
from jane.documents import JaneDocumentsValidationException
from jane.documents.models import DocumentIndex
from jane.documents.plugins import initialize_plugins


django.setup()


PATH = os.path.join(os.path.dirname(__file__), 'data')
FILES = {
    "usgs": os.path.join(PATH, 'usgs_event.xml'),
    "focmec": os.path.join(PATH, 'quakeml_1.2_focalmechanism.xml'),
    "private": os.path.join(PATH, "private_event.xml")
}


class QuakeMLPluginTestCase(TestCase):
    """
    Tests for the QuakeML plugin.

    This also tests a large part of jane.documents as it is so much easier
    to test with an actually working plugin. The quakeml plugin is a core
    plugin of Jane so this should be acceptable.
    """
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
             'geometry': [
                 Point(-117.6623333, 35.0476667),
                 MultiLineString([
                     LineString((-117.6623332999999860, 35.0521735816367155),
                                (-117.6623333, 35.0476667),
                                (-117.6623332999999860, 35.0431598150083872)),
                     LineString((-117.6568529607076101, 35.0476665762236408),
                                (-117.6623333, 35.0476667),
                                (-117.6678136392923619, 35.0476665762236408))])
                 ],
             'has_focal_mechanism': False,
             'has_moment_tensor': False,
             'horizontal_uncertainty_max': 500.0,
             'horizontal_uncertainty_max_azimuth': 0,
             'horizontal_uncertainty_min': 500.0,
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
             'geometry': [
                 Point(-120.2807, 42.138),
                 MultiLineString([
                     LineString((-120.2807, 42.2073215168237184),
                                (-120.2807, 42.1379999999999981),
                                (-120.2807, 42.0686776424464739)),
                     LineString((-120.18756038590098, 42.1379621973716567),
                                (-120.2807, 42.1379999999999981),
                                (-120.3738396140990119, 42.1379621973716567))])
                 ],
             'has_focal_mechanism': False,
             'has_moment_tensor': False,
             'horizontal_uncertainty_max': 7700.0,
             'horizontal_uncertainty_max_azimuth': 0,
             'horizontal_uncertainty_min': 7700.0,
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
             'horizontal_uncertainty_max': None,
             'horizontal_uncertainty_min': None,
             'horizontal_uncertainty_max_azimuth': None,
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

    def test_quakeml_uploading_modifying_deleting(self):
        """
        Test some more complex interactions.
        """
        path = "/rest/document_indices/quakeml"
        self.user.user_permissions.add(self.can_modify_quakeml_permission)

        # Upload a quakeml file with two events.
        with open(FILES["usgs"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake1.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.client.get(path).json()["results"]), 2)

        # Uploading the same file again will raise an error.
        with open(FILES["usgs"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake2.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(len(self.client.get(path).json()["results"]), 2)

        # Retrieve the indices for the one file directly.
        r = self.client.get("/rest/documents/quakeml/quake1.xml")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["indices"]), 2)

        # Modify the existing document.
        with open(FILES["focmec"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake1.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 204)
        # Only one remains.
        r = self.client.get(path).json()["results"]
        self.assertEqual(len(r), 1)
        # The focmec one has no latitude - easy to check
        self.assertIs(r[0]["indexed_data"]["latitude"], None)

        # Delete it. Unauthorized deletion does not work.
        r = self.client.delete("/rest/documents/quakeml/quake1.xml")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(len(self.client.get(path).json()["results"]), 1)

        # Authorize - it now should work.
        r = self.client.delete("/rest/documents/quakeml/quake1.xml",
                               **self.valid_auth_headers)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(len(self.client.get(path).json()["results"]), 0)

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

    def test_quakeml_validator(self):
        """
        Tests the QuakeML validator.
        """
        # Adding valid QuakeML files is tested enough in the other tests.
        # Here we just test adding an invalid file.
        self.user.user_permissions.add(self.can_modify_quakeml_permission)

        # QuakeML with no longitude.
        qml = b"""
           <?xml version='1.0' encoding='utf-8'?>
           <q:quakeml xmlns:q="http://quakeml.org/xmlns/quakeml/1.2"
                      xmlns="http://quakeml.org/xmlns/bed/1.2">
             <eventParameters
                 publicID="smi:local/ef7cc032-af32-4037-8e46-e021acdebb71">
               <event publicID="quakeml:eu.emsc/event/20120404_0000041">
                 <origin publicID="quakeml:eu.emsc/origin/rts/261020/782484">
                   <time>
                     <value>2012-04-04T14:21:42.300000Z</value>
                   </time>
                   <latitude>
                     <value>41.818</value>
                   </latitude>
                   <depth>
                     <value>1000.0</value>
                   </depth>
                   <depthType>from location</depthType>
                   <methodID>smi:eu.emsc-csem/origin_method/NA</methodID>
                 </origin>
               </event>
             </eventParameters>
           </q:quakeml>"""
        with self.assertRaises(JaneDocumentsValidationException):
            self.client.put("/rest/documents/quakeml/quake.xml",
                            data=qml, **self.valid_auth_headers)

        # Nothing should have been uploaded.
        self.assertEqual(len(self.client.get(
            "/rest/document_indices/quakeml",
            **self.valid_auth_headers).json()["results"]), 0)

    def test_quakeml_queries(self):
        """
        Test the REST queries for the QuakeML plugin.
        """
        path = "/rest/document_indices/quakeml"
        self.user.user_permissions.add(self.can_modify_quakeml_permission)

        # Upload files - should be two events.
        with open(FILES["usgs"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.client.get(
            path, **self.valid_auth_headers).json()["results"]), 2)

        # Just test a bunch of queries.
        self.assertEqual(len(self.client.get(
            path + "?min_latitude=43",
            **self.valid_auth_headers).json()["results"]), 0)
        self.assertEqual(len(self.client.get(
            path + "?min_latitude=42",
            **self.valid_auth_headers).json()["results"]), 1)
        self.assertEqual(len(self.client.get(
            path + "?min_latitude=30",
            **self.valid_auth_headers).json()["results"]), 2)
        self.assertEqual(len(self.client.get(
            path + "?min_latitude=30&min_longitude=-118",
            **self.valid_auth_headers).json()["results"]), 1)

        self.assertEqual(len(self.client.get(
            path + "?max_magnitude=1.56",
            **self.valid_auth_headers).json()["results"]), 1)

        self.assertEqual(len(self.client.get(
            path + "?magnitude_type=Md",
            **self.valid_auth_headers).json()["results"]), 1)
        self.assertEqual(len(self.client.get(
            path + "?magnitude_type=M*",
            **self.valid_auth_headers).json()["results"]), 2)

        self.assertEqual(len(self.client.get(
            path + "?agency=uw",
            **self.valid_auth_headers).json()["results"]), 1)
        self.assertEqual(len(self.client.get(
            path + "?!agency=ci",
            **self.valid_auth_headers).json()["results"]), 1)

        self.assertEqual(len(self.client.get(
            path + "?has_focal_mechanism=true",
            **self.valid_auth_headers).json()["results"]), 0)
        self.assertEqual(len(self.client.get(
            path + "?has_focal_mechanism=false",
            **self.valid_auth_headers).json()["results"]), 2)

        self.assertEqual(len(self.client.get(
            path + "?depth_in_m=0",
            **self.valid_auth_headers).json()["results"]), 1)
        self.assertEqual(len(self.client.get(
            path + "?min_depth_in_m=-2",
            **self.valid_auth_headers).json()["results"]), 2)
        self.assertEqual(len(self.client.get(
            path + "?min_depth_in_m=2",
            **self.valid_auth_headers).json()["results"]), 1)

        self.assertEqual(len(self.client.get(
            path + "?min_origin_time=2015-01-01",
            **self.valid_auth_headers).json()["results"]), 0)
        self.assertEqual(len(self.client.get(
            path + "?min_origin_time=2014-01-01",
            **self.valid_auth_headers).json()["results"]), 2)
        self.assertEqual(len(self.client.get(
            path + "?min_origin_time=2014-11-10",
            **self.valid_auth_headers).json()["results"]), 1)

        self.assertEqual(len(self.client.get(
            path + "?event_type=earthquake",
            **self.valid_auth_headers).json()["results"]), 0)
        self.assertEqual(len(self.client.get(
            path + "?!event_type=earthquake",
            **self.valid_auth_headers).json()["results"]), 2)
        self.assertEqual(len(self.client.get(
            path + "?event_type=quarry*",
            **self.valid_auth_headers).json()["results"]), 2)
        self.assertEqual(len(self.client.get(
            path + "?!event_type=quarry*",
            **self.valid_auth_headers).json()["results"]), 0)

        self.assertEqual(len(self.client.get(
            path + "?author=random",
            **self.valid_auth_headers).json()["results"]), 0)
        # All authors are None - so as soon as one searches for an author,
        # only results with an author will return something.
        # Changed: authors that are None will be returned if doing a search
        # only excluding a specific author
        self.assertEqual(len(self.client.get(
            path + "?!author=random",
            **self.valid_auth_headers).json()["results"]), 2)

        # Test the ordering.
        ev = self.client.get(path + "?ordering=depth_in_m").json()["results"]
        self.assertEqual(ev[0]["indexed_data"]["depth_in_m"], 0.0)
        self.assertEqual(ev[1]["indexed_data"]["depth_in_m"], 10.0)
        # Sorting by latitude will reverse the order.
        ev = self.client.get(path + "?ordering=latitude").json()["results"]
        self.assertEqual(ev[0]["indexed_data"]["depth_in_m"], 10.0)
        self.assertEqual(ev[1]["indexed_data"]["depth_in_m"], 0.0)

    def test_radial_query_quakeml(self):
        """
        Test radial queries with QuakeML.
        """
        # Be lazy and upload via REST.
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        with open(FILES["usgs"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.client.get(
            "/rest/document_indices/quakeml",
            **self.valid_auth_headers).json()["results"]), 2)

        # Actual location of one event.
        lat = 35.0476667
        lng = -117.6623333

        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml",
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 2)

        # Min radius.
        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", min_radius=0.1,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 1)

        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", min_radius=2,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 1)

        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", min_radius=10,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 0)

        # Max radius.
        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", max_radius=0.1,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 1)

        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", max_radius=2,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 1)

        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", max_radius=10,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 2)

        # Combinations of both.
        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", min_radius=1, max_radius=2,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 0)
        q = DocumentIndex.objects.get_filtered_queryset_radial_distance(
            document_type="quakeml", min_radius=1, max_radius=10,
            central_latitude=lat, central_longitude=lng)
        self.assertEqual(q.count(), 1)

    def test_get_distinct_values_quakeml(self):
        """
        Test getting distinct values from the QuakeML indices.
        """
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        with open(FILES["usgs"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.client.get(
            "/rest/document_indices/quakeml",
            **self.valid_auth_headers).json()["results"]), 2)

        self.assertEqual(sorted(DocumentIndex.objects.get_distinct_values(
            document_type="quakeml", json_key="agency")),
            ["ci", "uw"])

        self.assertEqual(sorted(DocumentIndex.objects.get_distinct_values(
            document_type="quakeml", json_key="event_type")),
            ["quarry blast"])

        # Failure condition 1: Not in meta dict of plugin.
        with self.assertRaises(Exception):
            DocumentIndex.objects.get_distinct_values(
                document_type="quakeml", json_key="bogus")

        # Failure condition 2: Not a string key.
        with self.assertRaises(Exception):
            DocumentIndex.objects.get_distinct_values(
                document_type="quakeml", json_key="latitude")

    def test_geometry_generation(self):
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        with open(FILES["usgs"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        path = "/rest/document_indices/quakeml"
        r = self.client.get(path).json()["results"][0]

        geo = r["geometry"]
        self.assertEqual(len(geo["coordinates"]), 2)
        self.assertEqual(len(geo["coordinates"][0]), 2)
        self.assertEqual(geo["type"], "GeometryCollection")
        # first geometry in collection is the point for the origin
        self.assertAlmostEqual(geo["coordinates"][0][0], -117.6623333)
        self.assertAlmostEqual(geo["coordinates"][0][1], 35.0476667)
        # second geometry in collection is the multilinestring with two lines
        # for horizontal uncertainties
        self.assertAlmostEqual(geo["coordinates"][1][0],
                               [[-117.66233329999999, 35.052173581636715],
                                [-117.6623333, 35.0476667],
                                [-117.66233329999999, 35.04315981500839]])
        self.assertAlmostEqual(geo["coordinates"][1][1],
                               [[-117.65685296070761, 35.04766657622364],
                                [-117.6623333, 35.0476667],
                                [-117.66781363929236, 35.04766657622364]])
        # The focmec one has no geometry.
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        with open(FILES["focmec"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake1.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        path = "/rest/document_indices/quakeml"
        r = self.client.get(path).json()["results"][-1]
        self.assertIs(r["geometry"], None)

    def test_content_type(self):
        """
        This is inferred from the plugin settings.
        """
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        with open(FILES["usgs"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        path = "/rest/document_indices/quakeml"
        r = self.client.get(path).json()["results"][0]

        self.assertEqual(r["data_content_type"], "text/xml")

    def test_adding_modifying_deleting_attachments(self):
        """
        Test attachment handling.
        """
        path = "/rest/document_indices/quakeml"

        # Upload an event.
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        with open(FILES["focmec"], "rb") as fh:
            r = self.client.put("/rest/documents/quakeml/quake.xml",
                                data=fh.read(), **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        r = self.client.get(path).json()["results"]
        self.assertEqual(len(r), 1)
        r = r[0]

        # No attachments currently exist.
        self.assertEqual(r["attachments_count"], 0)

        # Test the index.
        idx = r["id"]
        self.assertTrue(idx >= 1)

        a_path = path + "/%i/attachments" % idx
        r = self.client.get(a_path).json()
        self.assertEqual(
            r, {"count": 0, "next": None, "previous": None, "results": []})

        data_1 = b"Hello 1"
        data_2 = b"Hello 2"

        # Try to upload an attachment. First unauthorized.
        r = self.client.post(a_path, data=data_1, content_type="text/plain",
                             HTTP_CATEGORY="some_text")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.client.get(a_path).json()["count"], 0)

        # Authorized, but does not have the right permissions.
        r = self.client.post(a_path, data=data_1, content_type="text/plain",
                             HTTP_CATEGORY="some_text",
                             **self.valid_auth_headers)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.client.get(a_path).json()["count"], 0)

        # Add the correct permission.
        p = Permission.objects.filter(
            codename="can_modify_quakeml_attachments").first()
        self.user.user_permissions.add(p)
        r = self.client.post(a_path, data=data_1, content_type="text/plain",
                             HTTP_CATEGORY="some_text",
                             **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)

        # Retrieve and test the permission.
        r = self.client.get(a_path).json()
        self.assertEqual(r["count"], 1)
        r = r["results"][0]

        self.assertEqual(r["category"], "some_text")
        self.assertEqual(r["content_type"], "text/plain")
        self.assertEqual(r["created_by"], "random")
        self.assertEqual(r["modified_by"], "random")

        # Get the actual attachment.
        a_id = self.client.get(a_path).json()["results"][0]["id"]
        r = self.client.get(a_path + "/%i/data" % a_id)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"Hello 1")
        # Make sure its served with the correct content type.
        self.assertEqual(r["Content-Type"], "text/plain")

        # Update it.
        r = self.client.put(a_path + "/%i" % a_id,
                            data=data_2, content_type="text/random",
                            HTTP_CATEGORY="something_else",
                            **self.valid_auth_headers)

        r = self.client.get(a_path).json()
        self.assertEqual(r["count"], 1)
        r = r["results"][0]
        self.assertEqual(r["category"], "something_else")
        self.assertEqual(r["content_type"], "text/random")
        r = self.client.get(a_path + "/%i/data" % a_id)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"Hello 2")
        self.assertEqual(r["Content-Type"], "text/random")

        # Add another attachment.
        r = self.client.post(a_path, data=data_1, content_type="text/plain",
                             HTTP_CATEGORY="some_text",
                             **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get(a_path).json()["count"], 2)
        a_id_2 = self.client.get(a_path).json()["results"][-1]["id"]

        # Delete both. Must be authorized.
        r = self.client.delete(a_path + "/%i" % a_id)
        self.assertEqual(r.status_code, 401)

        # Revoke the permissions temporarily.
        self.user.user_permissions.remove(p)
        r = self.client.delete(a_path + "/%i" % a_id,
                               **self.valid_auth_headers)
        self.assertEqual(r.status_code, 401)

        # Delete them
        self.user.user_permissions.add(p)
        r = self.client.delete(a_path + "/%i" % a_id,
                               **self.valid_auth_headers)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.client.get(a_path).json()["count"], 1)
        r = self.client.delete(a_path + "/%i" % a_id_2,
                               **self.valid_auth_headers)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(self.client.get(a_path).json()["count"], 0)

        # Test failure when missing the category.
        r = self.client.post(a_path, data=data_1, content_type="text/plain",
                             **self.valid_auth_headers)
        self.assertEqual(r.status_code, 400)

    def test_documents_are_not_modified(self):
        """
        Tests that stored documents are not modified.
        """
        self.user.user_permissions.add(self.can_modify_quakeml_permission)
        with open(FILES["focmec"], "rb") as fh:
            data = fh.read()
        r = self.client.put("/rest/documents/quakeml/quake.xml",
                            data=data, **self.valid_auth_headers)
        self.assertEqual(r.status_code, 201)

        r = self.client.get("/rest/documents/quakeml/quake.xml/data")
        self.assertEqual(r.content, data)
