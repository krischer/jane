# -*- coding: utf-8 -*-

from jane.documents.plugins import ValidatorPluginPoint, IndexerPluginPoint, \
    ConverterPluginPoint


class StationValidatorPlugin(ValidatorPluginPoint):
    name = 'station'
    title = 'StationXML XMLSchema Validator'

    def validate(self, document):
        return True


class StationIndexerPlugin(IndexerPluginPoint):
    name = 'station'
    title = 'StationXML Indexer'

    def index(self, document):
        # prcoesssing

        # preview generiert
        image_string = document.plot()
        stream = read(document)


        return {
          "num_traces": 3,
          "traces": {},
          "__derived_data": [{"name": "preview", "mimetype": "png",
                              "": image_string}]

        }



class GeoJSONStationConverterPlugin(ConverterPluginPoint):
    format = 'geojson'

    def convert(self, document):
        return json2geojson(document)



class GeoJSONStationConverterPlugin(ConverterPluginPoint):
    format = 'geojson'

    def convert(self, document):
        return json2geojson(document)
