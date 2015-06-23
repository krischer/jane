# -*- coding: utf-8 -*-
import os
import sys
# import djcelery


DEBUG = True
SQL_DEBUG = False

# ensure PIL is working in virtualenv
try:
    import PIL.Image
    sys.modules['Image'] = PIL.Image
except ImportError:
    pass


if DEBUG is True:
    DEPLOYED = False
    TEMPLATE_DEBUG = True
else:
    DEPLOYED = True
    TEMPLATE_DEBUG = False


PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIRS = (os.path.join(PROJECT_DIR, 'templates'),)


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
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)
# project wide static directories besides app specific directories
STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)

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
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d ' +
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
# other required django apps
###############################################################################
INSTALLED_APPS += [
    'djangoplugins',
    'django_like',
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
    'PAGE_SIZE': 10
}


###############################################################################
# Celery (Task Queue)
###############################################################################
# djcelery.setup_loader()

INSTALLED_APPS += ['djcelery', 'corsheaders', 'kombu.transport.django']

# use RabbitMQ server
BROKER_URL = 'amqp://jane:jane@127.0.0.1:5672/jane'

CELERY_RESULT_BACKEND = "djcelery.backends.database:DatabaseBackend"

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = "json"


CORS_ORIGIN_ALLOW_ALL = True

TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'

###############################################################################
# django-debug-toolbar
# uncomment during initial syncdb/migrate
###############################################################################
INSTALLED_APPS += [
    'debug_toolbar',
    'template_timings_panel',
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

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'template_timings_panel.panels.TemplateTimings.TemplateTimings',
]

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


###############################################################################
# Import local settings
###############################################################################
try:
    from .local_settings import *  # NOQA @UnusedWildImport
except ImportError:
    print("ERROR: You need to copy local_settings.py.example into " +
          "local_settings.py and edit its content before running this "
          "service.")
    exit()


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
