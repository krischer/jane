# -*- coding: utf-8 -*-

from djangoplugins.point import PluginPoint


class ValidatorPluginPoint(PluginPoint):
    """
    """
    def validate(self):
        raise NotImplementedError


class IndexerPluginPoint(PluginPoint):
    """
    """
    def index(self):
        raise NotImplementedError


class ConverterPluginPoint(PluginPoint):
    """
    """
    def convert(self):
        raise NotImplementedError


class OutputConverterPluginPoint(PluginPoint):
    """
    """
    def convert(self):
        raise NotImplementedError


class InputConverterPluginPoint(PluginPoint):
    """
    """
    def convert(self):
        raise NotImplementedError
