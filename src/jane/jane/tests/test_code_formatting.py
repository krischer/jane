#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests all Python files of the project with flake8. This ensure PEP8 conformance
and some other sanity checks as well.
"""
import inspect
import os
import unittest

from distutils.version import LooseVersion
import flake8

flake8_version = LooseVersion(flake8.__version__)


class TestCodeFormatting(unittest.TestCase):
    def test_flake8(self):
        test_dir = os.path.dirname(os.path.abspath(inspect.getfile(
            inspect.currentframe())))
        jane_dir = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))

        # Possibility to ignore some files and paths.
        ignore_paths = [
            os.path.join(jane_dir, os.path.pardir, "docs"),
            os.path.join(jane_dir, os.path.pardir, ".git"),
            os.path.join(jane_dir, "jane", "documents", "migrations"),
            os.path.join(jane_dir, "jane", "waveforms", "migrations")
            ]

        ignore_files = [
            os.path.join(jane_dir, "jane", "local_settings.py")
            ]
        files = []
        for dirpath, _, filenames in os.walk(jane_dir):
            ignore = False
            for path in ignore_paths:
                if dirpath.startswith(path):
                    ignore = True
                    break
            if ignore:
                continue
            filenames = [_i for _i in filenames if
                         os.path.splitext(_i)[-1] == os.path.extsep + "py"]
            if not filenames:
                continue
            for py_file in filenames:
                full_path = os.path.join(dirpath, py_file)
                if full_path in ignore_files:
                    continue
                files.append(full_path)

        if flake8_version >= LooseVersion('3.0.0'):
            from flake8.api.legacy import get_style_guide
        else:
            from flake8.engine import get_style_guide

        flake8_kwargs = {'parse_argv': False}
        if flake8_version < LooseVersion('2.5.5'):
            import flake8.main
            flake8_kwargs['config_file'] = flake8.main.DEFAULT_CONFIG

        flake8_style = get_style_guide(**flake8_kwargs)
        report = flake8_style.check_files(files)

        self.assertEqual(len(report.get_statistics("")), 0)


if __name__ == "__main__":
    unittest.main()
