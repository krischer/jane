# REST Interface

Jane's REST interface can be used to query documents defined by plug-ins and
associated indices and attachments. By default Jane ships with StationXML and
QuakeML plug-ins but users can easily add their own. Additionally the REST
interface offers access to waveform data on a per-trace basis but this is
likely less useful than Jane's FDSNWS dataselect service which serves the same
data with a more convenient interface.

In the following `JANE_ROOT` will be used to denote the root address of a
running Jane server. The REST interface can then be accessed at
`JANE_ROOT/rest`.


## General Remarks

### Supported Data Formats

The data in the REST interface can mostly be queried in different formats -
choose whichever suites you best. If accessed from a web browser, a nice HTML
view will be served; otherwise it will default to `JSON` output. The `format`
argument can be used to request the data in different formats:

Format | URL
------------ | -------------
**JSON** | `JANE_ROOT/rest/something?format=json`
**XML** | `JANE_ROOT/rest/something?format=xml`
**YAML** | `JANE_ROOT/rest/something?format=yaml`
**JSONP** | `JANE_ROOT/rest/something?format=jsonp`
**Force the HTML API view** | `JANE_ROOT/rest/something?format=api`


### Pagination

Data in the REST interface is paginated, meaning that only a certain amount of
the available data is returned at any point. It can be controlled with two
query parameters:

Parameter    | Meaning
------------ | -------------
`limit`      | Controls the number of returned records.
`offset`     | Skip the given number of records.

The following URL for example will return records number 200 to 299:
`JANE_ROOT/rest/something?limit=100&offset=200`


### Authentication

Many actions and data require certain permissions, thus users have to
authenticate themselves. Within the HTML web API view, Django's sessions
authentication can be used; there is a nice button to log-in at the top right.
Another way to authenticate yourself is to use HTTP Basic authentication. For
all examples on this page we will assume a user named `user` with `pw` as a
password. Furthermore we will illustrate all examples with code snippets for
the Python [requests](http://python-requests.org) library, for
[HTTPie](http://httpie.org), a user-friendly command line client, and good ol'
`curl` itself.

##### Example using the Python [requests](http://python-requests.org) library:
```python
import requests
r = requests.get(url="JANE_ROOT/rest/...", auth=("user", "pw"))
```

##### Example using the [HTTPie](http://httpie.org) CLI client:
```bash
$ http -a user:pw JANE_ROOT/rest/...
```

##### Example using `curl`:
```bash
$ curl --user user:pw JANE_ROOT/rest/...
```

### HTTP Methods and Headers

Depending on the desired action, you might have to send the request with a
different HTTP method or additional headers. This section is a short tutorial
on how to do this.

##### Example using the Python [requests](http://python-requests.org) library:
```python
import requests

headers = {"category": "something"}

r = requests.get("JANE_ROOT/rest/...", headers=headers)
r = requests.put("JANE_ROOT/rest/...", headers=headers)
r = requests.post("JANE_ROOT/rest/...", headers=headers)
r = requests.delete("JANE_ROOT/rest/...", headers=headers)
```

##### Example using the [HTTPie](http://httpie.org) CLI client:
```bash
$ http JANE_ROOT/rest/... 'category:something'
$ http PUT JANE_ROOT/rest/... 'category:something'
$ http POST JANE_ROOT/rest/... 'category:something'
$ http DELETE JANE_ROOT/rest/... 'category:something'
```

##### Example using `curl`:
```bash
$ curl -H 'category: something' JANE_ROOT/rest/...
$ curl -X PUT -H 'category: something' JANE_ROOT/rest/...
$ curl -X POST -H 'category: something' JANE_ROOT/rest/...
$ curl -X DELETE -H 'category: something' JANE_ROOT/rest/...
```


## API Endpoints

This section presents a quick overview of all available endpoints including the
acceptable HTTP methods for each; they are explained in more detail further
down this page. Jane's REST API at points behaves a bit different from other
REST APIs: it might not offer a certain method or interpret it slightly
different. This is on purpose to provide as natural an API as possible tailored
to the capabilities of Jane.

#### General Endpoints

Endpoint | Available Methods | Description
------------ | ------------- | -----------
`JANE_ROOT/rest` | `GET` | Root of the REST interface.

#### Waveform Endpoints

All endpoints related to the waveform database of Jane. `ID` is the id of a
particular waveform trace.

Endpoint | Available Methods | Description
------------ | ------------- | -----------
`JANE_ROOT/rest/waveforms` | `GET` | List of all waveforms.
`JANE_ROOT/rest/waveforms/ID` | `GET` | REST resource for a particular waveform trace.
`JANE_ROOT/rest/waveforms/ID/plot` | `GET` | Plot of that trace.
`JANE_ROOT/rest/waveforms/ID/file` | `GET` | Data containing that trace.

#### Document Endpoints

Endpoints for the documents sorted by document type which is defined by the
plug-ins. Each document represents a file. Use this to upload new files,
updated versions of existing ones, or delete a whole document. `DOCTYPE`
denotes the document type defined by the plug-ins, `FILENAME` the name of a
particular document.

Endpoint | Available Methods | Description
------------ | ------------- | -----------
`JANE_ROOT/rest/documents` | `GET` | List of all document types.
`JANE_ROOT/rest/documents/DOCTYPE` | `GET` | List of all documents of that type.
`JANE_ROOT/rest/documents/DOCTYPE/FILENAME` | `GET`, `PUT`, `DELETE` | Get, create, or delete a document.
`JANE_ROOT/rest/documents/DOCTYPE/FILENAME/data` | `GET` | Get the data behind a certain document.

#### Document Index Endpoints

Endpoints for indices and attachments. Each document can have any number of
indices and each index can have any number of attachments. `DOCTYPE` denotes
the document type defined by the plug-ins, `ID` the id of a particular index,
and `AID` the id of particular attachment.

Endpoint | Available Methods | Description
------------ | ------------- | -----------
`JANE_ROOT/rest/document_indices`  | `GET` | List of all document types.
`JANE_ROOT/rest/document_indices/DOCTYPE`  | `GET` | List of all document indices of that type.
`JANE_ROOT/rest/document_indices/DOCTYPE/ID`  | `GET` | Get a certain document index.
`JANE_ROOT/rest/document_indices/DOCTYPE/ID/attachments`  | `GET`, `POST` | Get all or add a new attachment.
`JANE_ROOT/rest/document_indices/DOCTYPE/ID/attachments/AID`  | `GET`, `PUT`, `DELETE` | Get a certain, update an existing, or delete an attachment.
`JANE_ROOT/rest/document_indices/DOCTYPE/ID/attachments/AID/data` | `GET` | Get the data for a certain attachment.


## Waveforms

The API endpoint for the waveform data is at `JANE_ROOT/rest/waveforms`, see the table in the previous section for some sub-routes.

It can currently display all available traces including a picture and some meta
information. In the future it might evolve to do some different things so there
currently is not much more to say to this.

## Documents

The `JANE_ROOT/rest/documents` route is the entry point to the actual files on
which Jane's document database is built around.

#### List View

To get a list of all available documents of a certain document type, send, e.g.

```
GET JANE_ROOT/rest/documents/stationxml
```

#### Document View

Documents are identified via filename, which thus has to be unique per document
type.

```
GET JANE_ROOT/rest/documents/stationxml/BW.FURT.xml
```

#### Data

The REST API shows some information for each file, to download the actual file, do, e.g.

```
GET JANE_ROOT/rest/documents/stationxml/BW.FURT.xml/data
```

#### Add New Document

To create a new document, send a `PUT` request to a certain document URL, e.g.

```
PUT JANE_ROOT/rest/documents/stationxml/BW.FURT.xml
```

Let's say you want to upload the file `BW.FURT.xml`.

##### Example using the Python [requests](http://python-requests.org) library:
```python
import requests

with open("BW.FURT.xml", "rb") as fh:
    r = requests.put(
        url="JANE_ROOT/rest/documents/stationxml/BW.FURT.xml",
        auth=("user", "pw"),
        data=fh)

assert r.ok
```

##### Example using the [HTTPie](http://httpie.org) CLI client:
```bash
$ http -a user:pw PUT "JANE_ROOT/rest/documents/stationxml/BF.FURT.xml" < BW.FURT.xml
```

##### Example using `curl`:
```bash
$ curl --user user:pw \
  --data-binary @BW.FURT.XML \
  -X PUT "JANE_ROOT/rest/documents/stationxml/BF.FURT.xml"
```

#### Delete a Document

To delete a document, just send a `DELETE` request. Please keep in mind that
this will also delete all indices and potential attachments of the document.
The attachments might not be restorable if you have no backup.

```
DELETE JANE_ROOT/rest/documents/stationxml/BW.FURT.xml
```

##### Example using the Python [requests](http://python-requests.org) library:
```python
import requests

r = requests.delete(
    url="JANE_ROOT/rest/documents/stationxml/BW.FURT.xml",
    auth=("user", "pw"))

assert r.ok
```

##### Example using the [HTTPie](http://httpie.org) CLI client:
```bash
$ http -a user:pw DELETE "JANE_ROOT/rest/documents/stationxml/BF.FURT.xml"
```

##### Example using `curl`:
```bash
$ curl --user user:pw \
  -X DELETE "JANE_ROOT/rest/documents/stationxml/BF.FURT.xml"
```

#### Modify Existing Document

To modify an existing document, first delete it and then create a new one with
the same name. This is to safe-guard against accidentally overwriting exiting
documents including attachments.

## Document Indices

The `JANE_ROOT/rest/document_indices` route is the entry point to the indices,
    the core of Jane's document database.

#### List View

To get a list of all available indices of a certain document type, send, e.g.

```
GET JANE_ROOT/rest/document_indices/stationxml
```

##### Searching Over the Indices

Now the special thing here is that you can search over these indices and only
get a subset of indices that match your query. The keys that can be searched
over are determined by the `meta` attribute of the indexer plug-in for that
particular document type. In the case of the StationXML plugin it is defined as

```python
meta = {
    "network": "str",
    "station": "str",
    "location": "str",
    "channel": "str",
    "latitude": "float",
    "longitude": "float",
    "elevation_in_m": "float",
    "depth_in_m": "float",
    "start_date": "UTCDateTime",
    "end_date": "UTCDateTime",
    "sample_rate": "float",
    "sensor_type": "str"}
```

It is necessary to define this, as the available queries depend on the data
type. There are 5 possible data types: `"str"`, `"int"`, `"float"`, `"bool"`,
and `"UTCDateTime"`. Search parameters are appended to the URL and the type
of the parameters determines the available queries. Any number of them can
be combined. Identity queries can be negated by prefixing with an
exclamation mark. Furthermore as soon as you query a parameter and it is
`null` for a certain document, that document will not be returned even for
inequality queries.

###### Strings

Strings can be searched based on (in)equality. Wildcards can be used.

```
GET JANE_ROOT/rest/document_indices/stationxml?network=BW
GET JANE_ROOT/rest/document_indices/stationxml?network=B?
GET JANE_ROOT/rest/document_indices/stationxml?station=A*M
# An exclamation mark negates the query, meaning it will now return everything
# not containing the chosen string.
GET JANE_ROOT/rest/document_indices/stationxml?!network=BW
GET JANE_ROOT/rest/document_indices/stationxml?!network=B?
GET JANE_ROOT/rest/document_indices/stationxml?!station=A*M
```

###### Ints, Floats, and UTCDateTimes

These three types can be queried for (in)equality and smaller/larger.
`min_NAME` maps to `>=` and `max_NAME` to `<=` in the underlying SQL query.
Please keep in mind that (in)equality comparisons are extremely fragile for
floating point numbers and should not be used in almost all cases.

```
GET JANE_ROOT/rest/document_indices/stationxml?min_latitude=15.1&max_latitude=16.1
GET JANE_ROOT/rest/document_indices/stationxml?sample_rate=20.0
GET JANE_ROOT/rest/document_indices/stationxml?!sample_rate=20.0
```

###### Booleans

Booleans can only be searched for (in)equality.

```
GET JANE_ROOT/rest/document_indices/quakeml?public=true
GET JANE_ROOT/rest/document_indices/quakeml?public=false
GET JANE_ROOT/rest/document_indices/quakeml?!public=false
```

#### Index View

Indices are identified by their numeric id; get a certain index with, e.g.

```
GET JANE_ROOT/rest/document_indices/stationxml/1
```

#### Attachments List

To get a list of all attachments for a certain index, query, e.g.

```
GET JANE_ROOT/rest/document_indices/stationxml/1/attachments
```

#### Attachment

To get a certain attachment, you have to use the id of the attachment, e.g.

```
GET JANE_ROOT/rest/document_indices/stationxml/1/attachments/11
```

#### Attachment Data

The actual data of any attachment can be queried with

```
GET JANE_ROOT/rest/document_indices/stationxml/1/attachments/11/data
```


#### Add a New Attachment

Each index (here a single channel for a certain time interval in a StationXML
file) can have any number of attachments. Attachments might be created
during the initial upload of a document as part of the indexing process but
they can also be added, changed, and removed at a later stage.

Each attachment consists of the actual file that comprises the major part of an
attachment, an associated content type determining the type of file, and a
category which is just a string (usually a single word) to quickly describe the
attachment. Information about each attachment can be retrieved from the detail
view of any index.

##### Common Content Types

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

To create a new attachment, send a `POST` request to the attachments URL of a
certain index.

```
POST JANE_ROOT/rest/document_indices/stationxml/1/attachments
```

and add two HTTP headers:

* `content-type`: The content type.
* `Category`: The category/tag of the file.



Let's say you want to upload the picture `test.png`.

##### Example using the Python [requests](http://python-requests.org) library:
```python
import requests

headers = {"content-type": "image/png",
           "category": "random_image"}

with open("test.png", "rb") as fh:
    r = requests.post(
        url="JANE_ROOT/rest/document_indices/stationxml/1/attachments",
        auth=("user", "pw"),
        headers=headers,
        data=fh)

assert r.ok
```

##### Example using the [HTTPie](http://httpie.org) CLI client:
```bash
$ http -a user:pw POST "JANE_ROOT/rest/document_indices/stationxml/1/attachments" \
  'content-type:image/png' 'category:random_image' < test.png
```

##### Example using `curl`:
```bash
$ curl --user user:pw \
  --data-binary @test.png \
  -H 'content-type: image/png' -H 'category: random_image'
  -X POST "JANE_ROOT/rest/document_indices/stationxml/1/attachments"
```

#### Modify an Existing Document

The same logic hold true to modify an attachment, this time just send a `PUT`
request to the URL of a particular attachment.

```
PUT JANE_ROOT/rest/document_indices/stationxml/1/attachments/11
```

##### Example using the Python [requests](http://python-requests.org) library:
```python
import requests

headers = {"content-type": "image/png",
           "category": "random_image"}

with open("test.png", "rb") as fh:
    r = requests.put(
        url="JANE_ROOT/rest/document_indices/stationxml/1/attachments/11",
        auth=("user", "pw"),
        headers=headers,
        data=fh)

assert r.ok
```

##### Example using the [HTTPie](http://httpie.org) CLI client:
```bash
$ http -a user:pw PUT "JANE_ROOT/rest/document_indices/stationxml/1/attachments/11" \
  'content-type:image/png' 'category:random_image' < test.png
```

##### Example using `curl`:
```bash
$ curl --user user:pw \
  --data-binary @test.png \
  -H 'content-type: image/png' -H 'category: random_image'
  -X PUT "JANE_ROOT/rest/document_indices/stationxml/1/attachments/11"
```

#### Delete an Attachment

To delete an attachment, just send a `DELETE` request.

```
DELETE JANE_ROOT/rest/document_indices/stationxml/1/attachments/11
```

##### Example using the Python [requests](http://python-requests.org) library:
```python
import requests

r = requests.delete(
    url="JANE_ROOT/rest/document_indices/stationxml/1/attachments/11"
    auth=("user", "pw"))

assert r.ok
```

##### Example using the [HTTPie](http://httpie.org) CLI client:
```bash
$ http -a user:pw DELETE \
  "JANE_ROOT/rest/document_indices/stationxml/1/attachments/11"
```

##### Example using `curl`:
```bash
$ curl --user user:pw \
  -X DELETE "JANE_ROOT/rest/document_indices/stationxml/1/attachments/11"
```
