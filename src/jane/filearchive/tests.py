# -*- coding: utf-8 -*-

import datetime
import os

from django.test.testcases import TestCase

from jane.filearchive import models


class CoreTestCase(TestCase):
    def setUp(self):
        self.path = os.path.abspath(os.path.dirname(__file__))
        self.file = 'tests.py'

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
