# Jane Setup

This page details how to setup `Jane` on a production server. Most of these
steps only need to be done once but of course the availability of all these
service must be monitored and security critical updates must be applied to
maintain a stable installation.

## Dependencies of Jane

`Jane` depends on the following non-Python dependencies

* PostgreSQL 9.4
* PostGIS 2.1
* RabbitMQ 3.5

furthermore

* Python 3.4

and the following Python modules

* `obspy==0.10`
* `django==1.7`
* `celery`
* `django-celery`
* `watchdog`
* `psycopg2`
* `jsonfield`
* `django-plugins`
* `djangorestframework==2.4`
* `djangorestframework-gis==0.7`
* `markdown`
* `django-filter`
* `pyyaml`
* `defusedxml`
* `gdal`  On Windows: http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
* `geojson`
* `django-cors-headers`
* `django_like`
* `flake8`
* `django-debug-toolbar`
* `django-debug-toolbar-template-timings`
* `mkdocs`


## Installation of Python and the Dependencies

A simple way to install an up-to-date version of the dependencies is to use the Anaconda Python distribution. Once that is installed, the following two lines should do the trick:

```bash
$ conda install -c obspy obspy django==1.7 psycopg2 markdown flake8 gdal basemap pyyaml
$ pip install celery django-celery watchdog jsonfield django-plugins djangorestframework==2.4 djangorestframework-gis==0.7 defusedxml geojson django-cors-headers django_like django-debug-toolbar django-debug-toolbar-template-timings
```


## PostgreSQL Setup

PostgreSQL should also be run as a service via whatever mechanism your
operating system requires. It is also good practice to run PostgreSQL as
another non-root user to minimize the attack surface. The database name, user,
and password can of course be changed and be configured within `Jane`.

If you don't run PostgreSQL as a service (**DO NOT DO THIS IN PRODUCTION**),
you can initalize and start it with:

```bash
initdb -D /path/to/db
postgres -D /path/to/db
createuser --superuser postgres
```

Jane needs a database to work with. Here we will create a new database user
`jane` and a new database also called `jane`. You are free to choose the names
however you see fit.

```bash
createuser --encrypted --pwprompt jane
createdb --owner=jane jane
```

The last step is to enable the PostGIS extension for the just created database.

```bash
psql --command="CREATE EXTENSION postgis;" jane
```


## Start RabbitMQ for the job queue

RabbitMQ is the job queing system of choice for `Jane`. Again this is better run as a service.

```bash
$ rabbitmq-server
```


## Sync Django database

```bash
$ python manage.py syncdb
```

This should also sync the `Jane` plugins. If it does not, please run

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
