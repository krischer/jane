# REST Interface

The REST interface can be used to access the waveform files and to query the
document database. In the following `JANE_ROOT` will be used to denote the
address of the Jane server.

The REST interface can be accessed at

```
JANE_ROOT/rest
```

## General Things

The data in the REST interface can be queried in different formats. If accessed
from a web browser, a nice HTML view will be served; otherwise it will default
to `JSON` output. The `format` argument can be used to request the data in
different formats:

**JSON:** `JANE_ROOT/rest/something?format=json`

**XML:** `JANE_ROOT/rest/something?format=xml`

**YAML:** `JANE_ROOT/rest/something?format=yaml`

**JSONP:** `JANE_ROOT/rest/something?format=jsonp`

**Force the HTML API view:** `JANE_ROOT/rest/something?format=api`


## Waveforms

The API endpoint for the waveform data is at

```
JANE_ROOT/rest/waveforms
```

## Plugin Data

Jane's document database is based on the notion of plugins: Jane can thus store
different data types and index them. The REST interface offers a way to browse
and query these indices. The plugin defines what an index represents and which
indices can be queried over.

We will illustrate the plugin rest interface on the example of the StationXML
plugin that ships with Jane.

### List View

Each index represent a channel at a certain time interval. Navigate to

```
GET JANE_ROOT/stationxml
```
```json
[
    {"id": 475, ...},
    {"id": 476, ..."}
]
```

to get a list of all channels in the database.

### Data Download

It is of course possible to download the document associated with a particular
index. Please keep in mind that many indices potentially share one document.
Simple append the index and `data` to download the corresponding document.

```
GET JANE_ROOT/stationxml/475/data
```

### Detail View

Detailed information for a single index can be retrieved by appending the id to
the URL:

```
GET JANE_ROOT/stationxml/475
```
```json
{
    "id": 475,
    "url": "http://localhost:7000/rest/stationxml/475/",
    "document": 368,
    "data_url": "http://localhost:7000/rest/475/data/",
    "data_content_type": "text/xml",
    "created_at": "2015-05-01T17:31:12.182",
    "indexed_data": {
        "start_date": "2013-10-25T00:00:00.000000Z",
        "channel": "BHE",
        "network_name": "Mid-Atlantic Geophysical Integrative Collaboration",
        "network": "7A",
        "station_name": "Riverton, WV USA",
        "station": "CABN",
        "sample_rate": 40.0,
        "end_date": "2014-11-23T16:29:34.000000Z",
        "latitude": 38.7199,
        "location": "",
        "depth_in_m": 0.0,
        "longitude": -79.4412,
        "sensor_type": "Nanometrics Trillium 120 Sec Response/Taurus Stand",
        "elevation_in_m": 910.0
    },
    "geometry": {
        "type": "GeometryCollection",
        "geometries": [
            {
                "coordinates": [
                    -79.4412,
                    38.7199
                ],
                "type": "Point"
            }
        ]
    },
    "attachments": [
        {
            "id": 1,
            "url": "http://localhost:7000/rest/stationxml/475/1/",
            "category": "response",
            "content_type": "image/png",
            "created_at": "2015-05-01T17:31:12.188"
        }
    ]
}
```

### Searching Over the Indices

The indices can be searched over. The keys that can be searched over are
determined by the `meta` property of the indexer plugin. In the case of the
StationXML plugin it is defined as

```python
@property
def meta(self):
    return {
        "network": {"type": str},
        "station": {"type": str},
        "location": {"type": str},
        "channel": {"type": str},
        "latitude": {"type": float},
        "longitude": {"type": float},
        "elevation_in_m": {"type": float},
        "depth_in_m": {"type": float},
        "start_date": {"type": obspy.UTCDateTime},
        "end_date": {"type": obspy.UTCDateTime},
        "sample_rate": {"type": float},
        "sensor_type": {"type": str},
    }
```

It specifies the names and types of the keys that can be searched over.
Possible types are `str`, `float`, `int`, `bool`, and `obspy.UTCDateTime`
objects. Search parameters are appended to the URL and the type of the
parameters specifies the available searches. Any number of them can be
combined.

#### Strings

Strings can be searched based on equality. Wildcards can be used.

```
GET JANE_ROOT/rest/stationxml?network=BW
GET JANE_ROOT/rest/stationxml?network=B?
GET JANE_ROOT/rest/stationxml?station=A*M
```

#### Ints, Floats, and UTCDateTimes

These three types can be queried for equality and smaller/larger. `min_NAME`
maps to `>=` and `max_NAME` to `<=` in the underlying SQL query.

```
GET JANE_ROOT/rest/stationxml?min_latitude=15.1&max_latitude=16.1
GET JANE_ROOT/rest/stationxml?sample_rate=20.0
```

#### Booleans

Booleans can only be searched for equality.

```
GET JANE_ROOT/rest/quakeml?public=true
```


### Data Upload

To upload a new document, `POST` to the URL of the document type. One can
optionally specify the filename and the name of the document in the database by
passing custom HTTP headers. Both are not crucial for Jane to work but rather
serve documentary purposes.

Using `curl`:

```bash
$ curl -v \
    --data-binary @BW.FURT.xml \
    -H "Filename: /home/test/BW.FURT.xml" \
    -H "Name: BW.FURT.xml" \
    -X POST JANE_ROOT/rest/stationxml/
```

or the Python [requests](http://python-requests.org) library:

```python
import os
import requests

filename = "StationXML/BW.FURT.xml"

headers = {"Filename": filename,
           "Name": os.path.basename(filename)}

with open(filename, "rb") as fh:
    r = requests.post(
        url="http://localhost:7000/rest/stationxml/",
        data=fh,
        headers=headers)

assert r.ok
```

### Deleting Documents

This is not really REST compliant but fairly convenient to use. To delete a
documents and **ALL ASSOCIATED INDICES AND THEIR ATTACHMENTS** send a `DELETE`
request to any of the indices. Please be aware of the consequences!

With `curl`:

```bash
$ curl -v -X DELETE JANE_ROOT/rest/stationxml/590/
```

or the Python [requests](http://python-requests.org) library:

```python
import requests

r = requests.delete("JANE_ROOT/rest/stationxml/590/")
assert r.ok
```

### Modifying Documents

This is not really REST compliant but fairly convenient to use. To delete a
documents and **ALL ASSOCIATED INDICES AND THEIR ATTACHMENTS** send a `PUT`
request to any of the indices. Please be aware of the consequences: it will
delete any existing indices and attachments. It is possible to optionally pass
`filename` and `name` headers just like for uploading new documents.

Using `curl`:

```bash
$ curl -v \
    --data-binary @BW.FURT.xml \
    -H "Filename: /home/test/BW.FURT.xml" \
    -H "Name: BW.FURT.xml" \
    -X PUT JANE_ROOT/rest/stationxml/596/
```

or the Python [requests](http://python-requests.org) library:

```python
import os
import requests

filename = "StationXML/BW.FURT.xml"

headers = {"Filename": filename,
           "Name": os.path.basename(filename)}

with open(filename, "rb") as fh:
    r = requests.put(
        url="http://localhost:7000/rest/stationxml/596/",
        data=fh,
        headers=headers)

assert r.ok
```


## Dealing with Attachments

Each index (here a single channel for a certain time interval in a StationXML
file) can have any number of attachments. Attachments might be created during
the initial upload of a document as part of the indexing process but they can
also be added, changed, and removed at a later stage.

Each attachment consists of the actual file that comprises the major part of an
attachment, an associated content type determining the type of file, and a
category which is just a string (usually a single word) to quickly describe the
attachment. Information about each attachment can be retrieved from the detail
view of any index.

### Common Content Types

Here is a list of content types that you might want to use for the attachments.
Make sure to choose the correct one.

* **Bitmap Image:** `image/bmp`
* **GIF Image:** `image/gif`
* **JPEG Image:** `image/jpeg`
* **PDF File:**   `application/pdf`
* **PNG Image:** `image/png`
* **TIFF Image:** `image/tiff`
* **WebP Image:** `image/webp`
* **Google Earth - KML:** `application/vnd.google-earth.kml+xml`
* **Google Earth - Zipped KML:** `application/vnd.google-earth.kmz`
* **Microsoft Word:** `application/msword`
* **Zip Archive:** `application/zip`
* **Bzip2 Archive:** `application/x-bzip2`
* **CSV File:** `text/csv`
* **LaTeX File:** `application/x-latex`
* **Plain Text:** `text/plain`
* **XML File:** `application/xml`
* **YAML File:** `text/yaml`
* **Arbitrary Binary Data:** `application/octet-stream`


### Downloading Attachments

Just send an HTTP `GET` request to the attachment URL.

```
GET JANE_ROOT/stationxml/32/1/
```

In this case it would just return an image with the correct content-type of the
instrument for that particular channel.


### Uploading New Attachments

To add a new attachment, simply `POST` the binary data to the URL of an index
and add two HTTP headers:

* `Content-Type`: The content type.
* `Category`: The category/tag of the file.

Two example to illustrate how to do it. We will upload a file `image.png`, to
an index of the `stationxml` document type, having the category
`"random_image"`.

Using `curl`:

```bash
$ curl -v \
    --data-binary @image.png \
    -H "Content-Type: image/png" \
    -H "Category: random_image" \
    -X POST JANE_ROOT/rest/stationxml/590/
```

or the Python [requests](http://python-requests.org) library:

```python
import requests

headers = {"Content-Type": "image/png",
           "Category": "random_image"}

with open("image.png", "rb") as fh:
    r = requests.post(
        url="JANE_ROOT/rest/stationxml/590/",
        data=fh,
        headers=headers)

assert r.ok
```

### Deleting Attachments

Simply send a `DELETE` request to the given attachment; with `curl`:

```bash
$ curl -v -X DELETE JANE_ROOT/rest/stationxml/590/69/
```

or the Python [requests](http://python-requests.org) library:

```python
import requests

r = requests.delete("JANE_ROOT/rest/stationxml/590/69/")
assert r.ok
```

### Changing Attachments

To change an attachment `PUT` to the URL of the attachment with the same
parameters as when using `POST` to create a new one. Once again using `curl`:

```bash
$ curl -v \
    --data-binary @new_file.jpg \
    -H "Content-Type: image/jpeg" \
    -H "Category: new_image" \
    -X PUT JANE_ROOT/rest/stationxml/590/67/
```

or the Python [requests](http://python-requests.org) library:

```python
import requests

headers = {"Content-Type": "image/jpeg",
           "Category": "new_image"}

with open("new_file.jpg", "rb") as fh:
    r = requests.put(
        url="JANE_ROOT/rest/stationxml/590/67/",
        data=fh,
        headers=headers)

assert r.ok
```
