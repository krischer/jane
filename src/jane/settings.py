# -*- coding: utf-8 -*-
import os
import sys
import djcelery


DEBUG = True

# ensure PIL is working in virtualenv
try:
    import PIL.Image
    sys.modules['Image'] = PIL.Image
except ImportError:
    pass


if DEBUG is True:
    DEPLOYED = False
    TEMPLATE_DEBUG = True
    SQL_DEBUG = False
    DEBUG_TOOLBAR = True
else:
    DEPLOYED = True
    TEMPLATE_DEBUG = False
    DEBUG_TOOLBAR = False


PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIRS = (os.path.join(PROJECT_DIR, 'templates'),)


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']
APPEND_SLASH = True
TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-gb'
USE_I18N = False
USE_L10N = False
USE_TZ = False
DATETIME_FORMAT = "c"
DATE_FORMAT = "Y-m-d"


if DEPLOYED:
    MEDIA_ROOT = '/home/django/www/media'
    MEDIA_URL = '/media/'
    STATIC_ROOT = '/home/django/www/static'
    STATIC_URL = '/static/'
else:
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
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = [
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    # see http://docs.djangoproject.com/en/dev/ref/clickjacking/
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d ' + \
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
            'class': 'django.utils.log.NullHandler',
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
# django-plugins
###############################################################################
INSTALLED_APPS += [
    'djangoplugins',
]


###############################################################################
# Jane
###############################################################################
INSTALLED_APPS += [
    'jane.filearchive',
    'jane.documents',
    'jane.stations',
    'jane.quakeml',
]


###############################################################################
# Django REST framework
###############################################################################

INSTALLED_APPS += [
    'rest_framework',
]
REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.DjangoFilterBackend'
    ],
    # Default to 10
    'PAGINATE_BY': 10,
    # Allow client to override, using `?page_size=xxx`.
    'PAGINATE_BY_PARAM': 'page_size',
    # Maximum limit allowed when using `?page_size=xxx`.
    'MAX_PAGINATE_BY': 100
}


###############################################################################
# Celery (Task Queue)
###############################################################################
djcelery.setup_loader()

INSTALLED_APPS += ["djcelery"]
if DEPLOYED:
    # use RabbitMQ server
    BROKER_TRANSPORT = "amqp"
    BROKER_HOST = "127.0.0.1"
    BROKER_PORT = 5672
    BROKER_USER = "jane"
    BROKER_PASSWORD = "jane"
    BROKER_VHOST = "jane"
else:
    # use django db on local installation
    BROKER_URL = 'django://'
    INSTALLED_APPS += ['djcelery.transport']

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = "json"

# Modules to import when celeryd starts.
# This must import every module where you register tasks so celeryd
# is able to find and run them.
CELERY_IMPORTS = ["jane.filearchive.tasks"]


###############################################################################
# django-debug-toolbar
###############################################################################
INSTALLED_APPS += ['debug_toolbar']


###############################################################################
# Import local settings
###############################################################################
from .local_settings import *  # @UnusedWildImport


# speed up tests
if 'test' in sys.argv:
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
    DATABASES['default'] = {'ENGINE': 'django.db.backends.sqlite3'}
