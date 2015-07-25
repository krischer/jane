# Jane Setup

This page details how to setup `Jane` on a production server. Most of these
steps only need to be done once but of course the availability of all these
service must be monitored and security critical updates have to be applied to
maintain a stable installation.

## Dependencies of Jane

`Jane` depends on the following non-Python dependencies

* `PostgreSQL 9.4`
* `PostGIS 2.1`

and furthermore on

* `Python 3.4`

with the following Python modules

* `obspy==0.10`
* `django==1.8`
* `psycopg2`
* `jsonfield`
* `django-plugins`
* `djangorestframework==3.1`
* `djangorestframework-gis==0.8`
* `djangorestframework-jsonp`
* `djangorestframework-xml`
* `djangorestframework-yaml`
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
$ conda install -c obspy obspy django==1.8 psycopg2 markdown flake8 gdal pyyaml
$ pip install https://github.com/krischer/django-plugins/archive/master.zip
$ pip install https://github.com/krischer/django-like/archive/master.zip
$ pip install jsonfield djangorestframework==3.1 djangorestframework-gis==0.8 defusedxml geojson django-cors-headers django-debug-toolbar django-debug-toolbar-template-timings djangorestframework-jsonp djangorestframework-xml djangorestframework-yaml
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


## Initialize Django Database

This command will setup all necessary tables and what not.

```bash
$ python manage.py migrate
$ python manage.py createsupseruser
```
