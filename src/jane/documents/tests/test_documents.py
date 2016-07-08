# -*- coding: utf-8 -*-
import django
from django.test import TestCase

from jane.documents.plugins import initialize_plugins


django.setup()


class JaneDocumentsTestCase(TestCase):
    def setUp(self):
        # The test case class somehow messes with the plugins - thus we have
        # to initialize them all the time.
        initialize_plugins()

    def test_rest_root_view(self):
        r = self.client.get("/rest")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [
            {'available_traces': 0,
             'description': "REST view of Jane's waveform database",
             'name': 'waveforms',
             'url': 'http://testserver/rest/waveforms'},
            {'available_documents': 0,
             'description': "Jane's document database at the document level",
             'name': 'documents',
             'url': 'http://testserver/rest/documents'},
            {'available_indices': 0,
             'description': "Jane's document database at the index level",
             'name': 'document_indices',
             'url': 'http://testserver/rest/document_indices'}])

    def test_index_root_view(self):
        r = self.client.get("/rest/document_indices")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [
            {'available_documents': 0,
             'description': "QuakeML Plugin for Jane's Document Database",
             'document_type': 'quakeml',
             'url':
             'http://testserver/rest/document_indices/quakeml'},
            {'available_documents': 0,
             'description': "StationXML Plugin for Jane's Document Database",
             'document_type': 'stationxml',
             'url': 'http://testserver/rest/document_indices/stationxml'}])
