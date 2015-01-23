# Jane

## PostgreSQL Setup for Jane

This only needs to be done once. PostgreSQL should also be run as a service.

```bash
initdb -D /path/to/db
postgres -D /path/to/db
createuser --superuser postgres
createuser --createdb --no-createrole --no-superuser jane
createdb --owner=jane jane
psql --command="CREATE EXTENSION postgis;" jane
```


## Start RabbitMQ for the job queue

RabbitMQ is the job queing system of choice for Jane. Again this is better run as a service.

```bash
$ rabbitmq-server
```


## Sync Django database

```bash
$ python manage.py syncdb
```

This should also sync the Jane plugins. If it does not, please run

```bash
$ python manage.py syncplugins
```

## Start Celery workers

```bash
$ python manage.py celery worker -E -l info
```

This will launch as many workers as the machine has cores. The `-E` flags causes events to be sent so that tools celerymon and flower can work. The `-l info` flags sets the log level.

## Index a folder of waveform files

This can be used to initially add waveforms or to index a certain folder once.

```bash
$ python manage.py index_waveforms /path/to/waveforms
```

## Monitor folder of waveform files

This will continuously monitor a directory of waveform files for changes. All changes will be reflected in the database.

```bash
$ python manage.py filemon /path/to/waveforms
```

## Upload Plugin data

### Upload StationXML

```bash
$ python manage.py upload_documents stationxml /path/to/stationxml
```

### Upload QuakeML files

```bash
$ python manage.py upload_documents quakeml /path/to/quakeml
```



## Jane Internals

### Document Data Model

Jane stores data from plugins in a document database. The hierarchical data model is as follows:

* `DocumentType`: The document category. Determined from the installed plugins.
* `Document`: One document of a certain type. Can have multiple revisions.
* `DocumentRevision`: A certain revision of a document.
* `DocumentRevisionIndex`: The indices of a certain revision of a document.
* `DocumentRevisionIndexAttachments`: The attachments for one index.

    
