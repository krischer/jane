# Jane Setup

This page details how to setup and install `Jane`. 


## Dependencies of Jane

`Jane` depends on the following non-Python dependencies

* `PostgreSQL >= 9.4`
* `PostGIS >= 2.1`

and furthermore on

* `Python 3.4 or 3.5 or 3.6`

with the following Python modules

* `obspy`
* `django==1.9.x`
* `psycopg2`
* `djangorestframework<3.7`
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
* `geopy`
* `markdown`
* `mkdocs`
* `mkdocs-bootswatch`


## Installation of Python and the Dependencies

A simple way to install an up-to-date version of the dependencies is to use the
Anaconda Python distribution. Once Anaconda is installed, the following can be
used to setup a new dedicated and separate environment to run `Jane`:

```bash
$ conda config --add channels conda-forge
$ conda create -n jane python=3.6
$ conda activate jane
(jane)$ conda install django=1.9 obspy psycopg2 markdown flake8 gdal pyyaml pip geopy 'djangorestframework<3.7' djangorestframework-gis djangorestframework-xml djangorestframework-yaml django-debug-toolbar defusedxml geojson markdown mkdocs mkdocs-bootswatch
(jane)$ pip install djangorestframework-jsonp django-cors-headers django-plugins
```

Alternatively, the following Anaconda environment description file ...

```
name: jane
dependencies:
- python=3.5
- obspy
- psycopg2
- markdown
- flake8
- gdal
- geopy
- pyyaml
- pip
- pip:
  - django>=1.9,<1.10
  - djangorestframework<3.7
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
$ conda config --add channels conda-forge
$ conda env create -n jane -f jane_anaconda_env.txt
```

It is a good idea to pin the version of those packages that `Jane` depends on 
in a certain version (to avoid accidental updates). To do so put the following
content in a new file `/path/to/anaconda/envs/jane/conda-meta/pinned` (see
[http://conda.pydata.org/docs/faq.html#pinning-packages](http://conda.pydata.org/docs/faq.html#pinning-packages)):

```bash
python 3.6.*
obspy 1.1.*
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

## Installing Jane

```bash
cd /path/where/jane/should/live
git clone https://github.com/krischer/jane.git
cd jane
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

## Building the Documentation

Assuming `mkdocs` has been installed as above:

```
cd /path/to/jane/docs
./build_docs.sh
```

this will build and copy the build files to the correct directory.



## Installing on a Production Server

Things are very similar on a production server but you want to run most 
things as services and of course the availability of all these service must be 
monitored and security critical updates have to be applied to maintain a stable 
installation. Make sure to speak about this with your admin! We take no 
responsibilities for any security problems.

Properly deploying a Django application is well documented in the 
[official Django documentation](https://docs.djangoproject.com/en/1.9/howto/deployment/).

The fellowing is a shortened introduction on how to deploy it on a Debian 
server with an Apache webserver. Please note that `mod-wsgi-py3` for the 
Apache web server has to be the same Python with which `Jane` is run, so 
using the Anaconda Python is likely quite hard to do.

### PostgreSQL

Install with

```bash
sudo apt-get install postgresql postgresql-contrib postgis
```

make sure to get at least version 9.4. Then perform the basic setup (you 
must run this as the `postgres` user or whatever user PostgreSQL has been 
configured with):

```bash
createuser --encrypted --pwprompt jane
createdb --owner=jane jane
psql --command="CREATE EXTENSION postgis;" jane
```

### Python and Dependencies

We (as much as possible) rely on Debian packages. Sometimes we have to use 
`pip` if the Python module is not packaged. Make sure to install Python 3.4,
3.5 or 3.6!

First, add the ObsPy sources as written 
[here](https://github.com/obspy/obspy/wiki/Installation-on-Linux-via-Apt-Repository).

Then install as much as possible with `apt-get`:
 
```bash
# AS ROOT!
apt-get install python3-psycopg2 \
    python3-markdown \
    python3-yaml \
    python3-defusedxml \
    python3-gdal \
    python3-geopy \
    python3-flake8 \
    python3-pip \
    python3-obspy \
    ipython3 \
    git
```

And finally some things as a local user. You will likely want to create a 
separate user to run `Jane`. With that user, run (note that you might have 
to use `pip3` instead of `pip`):
 
```bash
# AS USER!
pip3 install --user \
    "django>=1.9,<1.10" \
    "djangorestframework<3.7" \
    djangorestframework-gis \
    djangorestframework-jsonp \
    djangorestframework-xml \
    djangorestframework-yaml \
    django-cors-headers \
    django-debug-toolbar \
    django-plugins \
    geojson \
    mkdocs \
    mkdocs-bootswatch
```

Then follow the instructions above to get `Jane` from Github, adapt the 
`local_settings.py` file, and build the documentation.

Finally also run a couple of `manage.py` commands (you might have to use 
`python3`). The `collectstatic` command will copy all static files to a 
common directory that is then served directly by Apache making it much faster:

```bash
cd jane/src
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py collectstatic
```

### Configuring Apache

The last thing to do is to configure Apache to run `Jane` over the `WSGI`.

Install it with

```bash
sudo apt-get install apache2 libapache2-mod-wsgi-py3
sudo a2enmod wsgi
```

make sure its running

```bash
/etc/init.d/apache2 status
```

The `VirtualHost` configuration has to look approximately like this (details 
will of course differ per installation):

```apache
<VirtualHost *:80>
        WSGIDaemonProcess jane user=jane 
        python-path=/path/to/jane/jane/src:/path/to/site-packages processes=4 threads=8
        WSGIProcessGroup jane
        WSGIScriptAlias / /path/to/jane/jane/src/jane/wsgi.py
        WSGIPassAuthorization On
        WSGIApplicationGroup %{GLOBAL}

        <Directory /path/to/jane/jane/src/jane>
                <Files wsgi.py>
                Require all granted
                </Files>
        </Directory>

        # Prevent django from serving static files
        DocumentRoot /path/to/jane/jane/static
        Alias /static /path/to/jane/jane/static
        <Directory /path/to/jane/jane/static>
                Require all granted
        </Directory>
        
        ...

</VirtualHost>
```

Make sure to choose sensible `processes` and `threads` options.

### Troubleshooting

When running `python3 manage.py runserver` the following error traceback shows up:

```
  [...]
  File ".../lib/python3.6/site-packages/django/contrib/gis/geos/libgeos.py", line 171, in geos_version_info
    raise GEOSException('Could not parse version info string "%s"' % ver)
django.contrib.gis.geos.error.GEOSException: Could not parse version info string "3.6.2-CAPI-1.10.2 0"
```

See [#78](https://github.com/krischer/jane/pull/78) and monkey patch the above file `libgeos.py` by adding a `?` after the `r` in the regex pattern like shown [here](https://github.com/krischer/jane/blob/45862359dc385a3518b4d080ac7336ad78ec85c5/.travis.yml#L45).

---

When running `python3 manage.py runserver` the following error traceback shows up:

```
  [...]
  File ".../lib/python3.6/site-packages/rest_framework/compat.py", line 21, in <module>
    from django.urls import (  # noqa
ModuleNotFoundError: No module named 'django.urls'
```

Check version of `django-restframework`. `django-restframework`>= 3.7 does not work together with Django 1.9, so downgrade `django-restframework` if it is a higher version. See [#78](https://github.com/krischer/jane/pull/78).
