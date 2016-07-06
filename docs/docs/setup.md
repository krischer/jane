# Jane Setup

This page details how to setup and install `Jane`. 


## Dependencies of Jane

`Jane` depends on the following non-Python dependencies

* `PostgreSQL 9.4`
* `PostGIS 2.1`

and furthermore on

* `Python 3.4`

with the following Python modules

* `obspy`
* `django==1.9.x`
* `psycopg2`
* `djangorestframework`
* `djangorestframework-gis`
* `djangorestframework-jsonp`
* `djangorestframework-xml`
* `djangorestframework-yaml`
* `django-cors-headers`
* `django-debug-toolbar`
* `django-plugins` 
* `defusedxml`
* `flake8`
* `gdal`  ([see here for Windows](http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal))
* `geojson`
* `markdown`
* `mkdocs`
* `mkdocs-bootswatch`


## Installation of Python and the Dependencies

A simple way to install an up-to-date version of the dependencies is to use the
Anaconda Python distribution. Once Anaconda is installed, the following can be
used to setup a new dedicated and separate environment to run `Jane`:

```bash
$ conda config --add channels obspy
$ conda create -n jane python=3.4
$ source activate jane
(jane)$ conda install obspy psycopg2 markdown flake8 gdal pyyaml pip
# Install the latest 1.9.x release.
(jane)$ pip install "django>=1.9,<1.10"
(jane)$ pip install djangorestframework djangorestframework-gis djangorestframework-jsonp djangorestframework-xml djangorestframework-yaml django-cors-headers django-debug-toolbar django-plugins defusedxml geojson markdown mkdocs mkdocs-bootswatch
```

Alternatively, the following Anaconda environment description file ...

```
name: jane
dependencies:
- python=3.4
- obspy
- psycopg2
- markdown
- flake8
- gdal
- pyyaml
- pip
- pip:
  - django>=1.9,<1.10
  - djangorestframework
  - djangorestframework-gis
  - djangorestframework-jsonp
  - djangorestframework-xml
  - djangorestframework-yaml
  - django-cors-headers
  - django-debug-toolbar
  - django-plugins
  - defusedxml
  - geojson
  - markdown
  - mkdocs
  - mkdocs-bootswatch
```

... can be used to create the environment (save as file 
`jane_anaconda_env.txt`):


```bash
$ conda config --add channels obspy
$ conda env create -n jane -f jane_anaconda_env.txt
```

It is a good idea to pin the version of those packages that `Jane` depends on 
in a certain version (to avoid accidental updates). To do so put the following
content in a new file `/path/to/anaconda/envs/jane/conda-meta/pinned` (see
[http://conda.pydata.org/docs/faq.html#pinning-packages](http://conda.pydata.org/docs/faq.html#pinning-packages)):

```bash
python 3.4.*
obspy 1.0.*
```

After everything has been installed, make sure to run the tests as explained
[on the testing page](testing.md) to make sure the installation is valid.

## PostgreSQL Setup

PostgreSQL should also be run as a service via whatever mechanism your
operating system requires. It is also good practice to run PostgreSQL as
another non-root user to minimize the attack surface. The database name, user,
and password can of course be changed and be configured within `Jane`.

If you don't run PostgreSQL as a service (**DO NOT DO THIS IN PRODUCTION**),
you can initalize and start it with:

```bash
$ initdb -D /path/to/db
$ postgres -D /path/to/db

# All the following commands will have to be executed in a separate shell.
$ createuser --superuser postgres  # required for pgadmin
```

`Jane` needs a database to work with. Here we will create a new database user
`jane` and a new database also called `jane`. You are free to choose the names
however you see fit, just make sure they are the same as in your 
`local_settings.py` file.

```bash
$ createuser --encrypted --pwprompt jane
$ createdb --owner=jane jane
```

The last step is to enable the PostGIS extension for the just created database.

```bash
$ psql --command="CREATE EXTENSION postgis;" jane
```

## Adapt Local Settings

Copy `jane/src/local_settings.py.example` to `jane/src/local_settings.py` and 
fill in the database and user name and credentials. Also have a look at the
[available settings](settings.md) to customize your `Jane` installation.


## Initialize Django Database

This command will setup all necessary tables and what not. All 
`python manage.py` commands have to be executed in the `jane/src` folder or 
use an absolute path to the `manage.py` file.

```bash
$ python manage.py migrate
$ python manage.py createsuperuser
```

## Run Jane

To test the setup, run `Jane` with ...

```bash
$ python manage.py runserver
```

... which will launch a local web server.
