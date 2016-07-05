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

* `obspy`
* `django`
* `psycopg2`
* `django-plugins` (https://github.com/krischer/django-plugins/archive/django1.9.zip)
* `djangorestframework`
* `djangorestframework-gis`
* `djangorestframework-jsonp`
* `djangorestframework-xml`
* `djangorestframework-yaml`
* `markdown`
* `django-filters`
* `defusedxml`
* `gdal`  On Windows: http://www.lfd.uci.edu/~gohlke/pythonlibs/#gdal
* `geojson`
* `django-cors-headers`
* `flake8`
* `django-debug-toolbar`
* `mkdocs`


## Installation of Python and the Dependencies

A simple way to install an up-to-date version of the dependencies is to use the
Anaconda Python distribution. Once Anaconda is installed, the following can be
used to setup a new dedicated and separate environment to run `Jane`:

```bash
$ conda config --add channels obspy
$ conda create -n jane python=3.4
$ source activate jane
(jane)$ conda install obspy psycopg2 markdown flake8 gdal pyyaml
(jane)$ pip install django==1.9
(jane)$ pip install https://github.com/krischer/django-plugins/archive/django1.9.zip
(jane)$ pip install jsonfield djangorestframework djangorestframework-gis defusedxml geojson django-cors-headers django-debug-toolbar django-debug-toolbar-template-timings djangorestframework-jsonp djangorestframework-xml djangorestframework-yaml
```

Alternatively, the following Anaconda environment description file..

```
name: jane
dependencies:
- django
- flake8
- gdal
- markdown
- obspy
- psycopg2
- python=3.4
- pyyaml
- sqlparse
- pip:
  - defusedxml
  - django-cors-headers
  - django-debug-toolbar
  - https://github.com/krischer/django-plugins/archive/django1.9.zip
  - djangorestframework
  - djangorestframework-gis
  - djangorestframework-jsonp
  - djangorestframework-xml
  - djangorestframework-yaml
  - geojson
  - jsonfield
```

..can be used to create the environment (save as file `jane_anaconda_env.txt`,
exact version numbers of packages might have to be adapted to available package
versions in the future):

```bash
$ conda config --add channels obspy
$ conda env create -n jane -f jane_anaconda_env.txt
```

The following exact version setup has been run successfully:

```
name: jane_exact_versions
dependencies:
- django=1.8.4=py34_0
- flake8=2.5.1=py34_0
- fontconfig=2.11.1=5
- freetype=2.5.5=0
- future=0.15.2=py34_0
- gdal=2.0.0=py34_1
- geos=3.4.2=0
- get_terminal_size=1.0.0=py34_0
- hdf4=4.2.11=0
- hdf5=1.8.15.1=2
- ipython=4.2.0=py34_0
- ipython_genutils=0.1.0=py34_0
- jpeg=8d=0
- kealib=1.4.5=0
- libgdal=2.0.0=2
- libgfortran=3.0=0
- libnetcdf=4.3.3.1=3
- libpng=1.6.17=0
- libxml2=2.9.2=0
- libxslt=1.1.28=0
- lxml=3.6.0=py34_0
- markdown=2.6.6=py34_0
- matplotlib=1.4.3=np19py34_2
- mccabe=0.3.1=py34_0
- mkl=11.3.1=0
- nose=1.3.7=py34_0
- numpy=1.9.3=py34_2
- obspy=1.0.1=py34_0
- openssl=1.0.2g=0
- path.py=8.2.1=py34_0
- pep8=1.7.0=py34_0
- pexpect=4.0.1=py34_0
- pickleshare=0.5=py34_0
- pip=8.1.1=py34_1
- proj.4=4.9.1=0
- proj4=4.9.1=0
- psycopg2=2.6.1=py34_1
- ptyprocess=0.5=py34_0
- pyflakes=1.1.0=py34_0
- pyparsing=2.0.3=py34_0
- pyproj=1.9.4=py34_1
- pyqt=4.11.4=py34_1
- python=3.4.4=0
- python-dateutil=2.5.2=py34_0
- pytz=2016.3=py34_0
- pyyaml=3.11=py34_1
- qt=4.8.7=1
- readline=6.2=2
- requests=2.9.1=py34_0
- scipy=0.17.0=np19py34_2
- setuptools=20.7.0=py34_0
- simplegeneric=0.8.1=py34_0
- sip=4.16.9=py34_0
- six=1.10.0=py34_0
- sqlalchemy=1.0.12=py34_0
- sqlite=3.9.2=0
- tk=8.5.18=0
- traitlets=4.2.1=py34_0
- wheel=0.29.0=py34_0
- xerces-c=3.1.2=0
- xz=5.0.5=1
- yaml=0.1.6=0
- zlib=1.2.8=0
- pip:
  - backports.shutil-get-terminal-size==1.0.0
  - defusedxml==0.4.1
  - django-cors-headers==1.1.0
  - django-debug-toolbar==1.4
  - django-debug-toolbar-template-timings==0.6.6
  - django-dirtyfields==0.8.2
  - https://github.com/krischer/django-plugins/archive/master.zip
  - djangorestframework==3.3.3
  - djangorestframework-gis==0.10.1
  - djangorestframework-jsonp==1.0.2
  - djangorestframework-xml==1.3.0
  - djangorestframework-yaml==1.0.3
  - geojson==1.3.2
  - ipython-genutils==0.1.0
  - jsonfield==1.0.3
  - sqlparse==0.1.19
```

It is a good idea to pin the version of those packages that `Jane` depends on in
a certain version (to avoid accidental updates). To do so put the following
content in a new file `/path/to/anaconda/envs/jane/conda-meta/pinned` (see
http://conda.pydata.org/docs/faq.html#pinning-packages):

```
python 3.4.*
obspy 1.0.*
django 1.8.*
```

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
$ createuser --superuser postgres
```

Jane needs a database to work with. Here we will create a new database user
`jane` and a new database also called `jane`. You are free to choose the names
however you see fit.

```bash
$ createuser --encrypted --pwprompt jane1
$ createdb --owner=jane1 jane1A
```

The last step is to enable the PostGIS extension for the just created database.

```bash
$ psql --command="CREATE EXTENSION postgis;" jane1A
```

## Adapt Local Settings

Copy `local_settings.py.example` to `local_settings.py` and fill in the
database and user name and credentials.


## Initialize Django Database

This command will setup all necessary tables and what not.

```bash
$ python manage.py migrate
$ python manage.py createsuperuser
```

## Run Jane

To test the setup, run Jane with..

```bash
$ python manage.py runserver
```
