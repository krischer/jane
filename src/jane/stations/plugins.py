# -*- coding: utf-8 -*-

from jane.documents.plugins import ValidatorPluginPoint, IndexerPluginPoint


class StationValidatorPlugin(ValidatorPluginPoint):
    name = 'station'
    title = 'StationXML XMLSchema Validator'

    def validate(self, document):
        return True


class StationIndexerPlugin(IndexerPluginPoint):
    name = 'station'
    title = 'StationXML Indexer'

    @property
    def meta(self):
        """
        types: string, date, datetime, bool, int, float
        """
        return {'num_traces': {'type': 'string',
                               'minimum_allowed': True,
                               'wildcard_allowed': True}
        }

    def index(self, document):
        return []
