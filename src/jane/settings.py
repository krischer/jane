# -*- coding: utf-8 -*-

import os
import sys


DEBUG = True
SQL_DEBUG = False


if DEBUG is True:
    DEPLOYED = False
    _TEMPLATE_DEBUG = True
else:
    DEPLOYED = True
    _TEMPLATE_DEBUG = False


PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']
APPEND_SLASH = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-gb'
USE_I18N = False
USE_L10N = False
USE_TZ = False
DATETIME_FORMAT = "c"
DATE_FORMAT = "Y-m-d"


MEDIA_ROOT = os.path.abspath(os.path.join(PROJECT_DIR, '..', '..',
                                          'media'))
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.abspath(os.path.join(PROJECT_DIR, '..', '..',
                                           'static'))
STATIC_URL = '/static/'


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)
# project wide static directories besides app specific directories
STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
)

# List of callables that know how to import templates from various sources.
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [
        os.path.join(PROJECT_DIR, "templates"),
    ],
    'OPTIONS': {
        'debug': _TEMPLATE_DEBUG,
        'context_processors': (
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.debug',
            'django.template.context_processors.i18n',
            'django.template.context_processors.media',
            'django.template.context_processors.static',
            'django.template.context_processors.tz',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.request',
        ),
        'loaders': (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader'
        )
    }
}]


MIDDLEWARE_CLASSES = [
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # see http://docs.djangoproject.com/en/dev/ref/clickjacking/
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'jane.jane.middleware.AutoLogoutMiddleware',
]


ROOT_URLCONF = 'jane.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'jane.wsgi.application'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
]

# https://docs.djangoproject.com/en/dev/topics/logging/
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format':
                '%(levelname)s %(asctime)s %(module)s %(process)d '
                '%(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'WARN',
        },
        'django.db.backends': {
            'handers': ['console'],
            'level': 'WARN',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}

if not DEPLOYED and SQL_DEBUG:
    LOGGING['loggers']['django.db.backends']['level'] = 'DEBUG'

if DEPLOYED:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


###############################################################################
# other required django apps
###############################################################################
INSTALLED_APPS += [
    'djangoplugins',
]


###############################################################################
# Django REST framework
###############################################################################
INSTALLED_APPS += [
    'rest_framework',
    'rest_framework_gis',
]
REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),

    'DEFAULT_PARSER_CLASSES': (
        'jane.documents.parsers.JaneDocumentUploadParser',
    ),

    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'jane.jane.renderers.JaneBrowsableAPIRenderer',
        # Starting with DRF 3, some renderers get moved to separate modules.
        'rest_framework_xml.renderers.XMLRenderer',
        'rest_framework_yaml.renderers.YAMLRenderer',
        'rest_framework_jsonp.renderers.JSONPRenderer'
    ),

    # Pagination. This one here gives access to `limit` and `offset`
    # parameters and still has nice page numbers in the web API.
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.LimitOffsetPagination',
    # Default to 10.
    'PAGE_SIZE': 10,

    'EXCEPTION_HANDLER':
        'jane.jane.rest_exception_handler.custom_exception_handler'
}


###############################################################################
# corsheader
###############################################################################
INSTALLED_APPS += ['corsheaders']

CORS_ORIGIN_ALLOW_ALL = True


###############################################################################
# django-debug-toolbar
###############################################################################
INSTALLED_APPS += [
    'debug_toolbar',
]


def show_toolbar(request):
    try:
        if not request.user.is_superuser:
            return False
        return True
    except AttributeError:
        return False
    else:
        return False


DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': 'jane.settings.show_toolbar',
}


###############################################################################
# Jane Apps
###############################################################################
INSTALLED_APPS += [
    'jane.jane',
    'jane.waveforms',
    'jane.documents',
    'jane.stationxml',
    'jane.quakeml',
    'jane.fdsnws'
]


###############################################################################
# Jane Default Config
###############################################################################

# Name of the instance used in parts of the web interface.
JANE_INSTANCE_NAME = "Jane"
# Color used in certain parts of the web interface. Useful to distinguish
# separate Jane installations.
JANE_ACCENT_COLOR = "#D9230F"
# Constants written to StationXML files created by Jane.
JANE_FDSN_STATIONXML_SENDER = "Jane"
JANE_FDSN_STATIONXML_SOURCE = "Jane"

###############################################################################
# Import local settings
###############################################################################
try:
    from .local_settings import *  # NOQA @UnusedWildImport
    from .local_settings import (
        ADDITIONAL_INSTALLED_APPS, ADDITIONAL_MIDDLEWARE_CLASSES)
except ImportError:
    print("ERROR: You need to copy local_settings.py.example into " +
          "local_settings.py and edit its content before running this "
          "service.")
    exit()
# add additional apps from local_settings, if any
INSTALLED_APPS.extend(ADDITIONAL_INSTALLED_APPS)
for name, placement in ADDITIONAL_MIDDLEWARE_CLASSES.items():
    before = placement.get('before', [])
    after = placement.get('after', [])
    before_index = len(MIDDLEWARE_CLASSES)
    after_index = -1
    # try to find the mentioned classes in the middleware and determine where
    # the additional middleware should be inserted
    # searching through list: https://stackoverflow.com/a/9542768
    for name_ in before:
        before_index = min(
            next((i for i, item in enumerate(MIDDLEWARE_CLASSES)
                  if item == name_), before_index),
            before_index)
    for name_ in after:
        after_index = max(
            next((i for i, item in enumerate(MIDDLEWARE_CLASSES)
                  if item == name_), after_index),
            after_index)
    if before_index <= after_index:
        msg = ("Can not insert additional middleware class '{}' from "
               "local_settings.py because before/after constraints can not "
               "be satisfied.").format(name)
        raise Exception(msg)
    MIDDLEWARE_CLASSES.insert(before_index, name)


# speed up tests
if 'test' in sys.argv:
    print("Using test settings ...")
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    DEBUG = False
    TEMPLATE_DEBUG = False
    import logging
    logging.disable(logging.CRITICAL)
    # set live test server
    os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = 'localhost:8082'
