#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests all Python files of the project with flake8. This ensure PEP8 conformance
and some other sanity checks as well.
"""
import flake8
import flake8.engine
import flake8.main
import inspect
import os
import unittest


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
                files.append(full_path)

        # Get the style checker with the default style.
        flake8_style = flake8.engine.get_style_guide(
            parse_argv=False, config_file=flake8.main.DEFAULT_CONFIG)

        report = flake8_style.check_files(files)

        # Make sure at least 4 files are tested.
        self.assertTrue(report.counters["files"] >= 4)
        # And no errors occured.
        self.assertEqual(report.get_count(), 0)


if __name__ == "__main__":
    unittest.main()
