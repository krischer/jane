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
# project wide static directories besides app specific directories
STATICFILES_DIRS = (
    os.path.join(PROJECT_DIR, 'static'),
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
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # see http://docs.djangoproject.com/en/dev/ref/clickjacking/
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'jane.jane.middleware.WhoDidItMiddleware',
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
    'jane.waveforms',
    'jane.documents',
    'jane.stationxml',
    'jane.quakeml',
    'jane.jane'
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

    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework.renderers.XMLRenderer',
        'rest_framework.renderers.YAMLRenderer',
        'rest_framework.renderers.JSONPRenderer'
    ),

    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    # 'DEFAULT_PERMISSION_CLASSES': [
    #     'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    # ],
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
# djcelery.setup_loader()

INSTALLED_APPS += ["djcelery", "corsheaders"]
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
    INSTALLED_APPS += ['kombu.transport.django']

CELERY_RESULT_BACKEND = "djcelery.backends.database:DatabaseBackend"

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = "json"


CORS_ORIGIN_ALLOW_ALL = True

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

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
# Import local settings
###############################################################################
try:
    from .local_settings import *  # @UnusedWildImport
except ImportError:
    print("ERROR: You need to copy local_settings.py.example into " + \
        "local_settings.py and edit its content before running this service.")
    exit()

# speed up tests
if 'test' in sys.argv:
    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )
