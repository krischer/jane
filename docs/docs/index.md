# Welcome to the Jane Documentation

Jane is a database for seismological data specially suited for small to medium
size observatories.


## Setup

The fairly long setup is detailed on a [seperate page](setup.md).


## Jane Internals

A description of the inner workings of Jane can be found [here](internals.md).


## Jane

Jane has essentially two components, a waveform database storing seismological
data traces and a document database storing arbitrary things.

### Document Plugins

To add support for a new type of document, one has to write a plugin and
provide at least a validator for the chosen data format and an indexer. Each
validator will be run upon uploading a file and has to return either `True` or
`False`. Files that return `False` for any of the registered validators will be
rejected.

An index is always a Python dictionary. Each indexer is thus supposed to return
a list of dictionaries.

#### Uploading New Documents

To upload new documents, use the `upload_document` manage command.

```bash
$ python manage.py upload_documents DOCUMENT_TYPE /path/to/document
```

**Uploading StationXML:**

```bash
$ python manage.py upload_documents stationxml /path/to/stationxml
```

**Uploading QuakeML:**

```bash
$ python manage.py upload_documents quakeml /path/to/quakeml
```
