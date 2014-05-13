# -*- coding: utf-8 -*-

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'jane',
        'USER': 'jane',
        'PASSWORD': 'jane',
        'HOST': '127.0.0.1',
        'PORT': 5433,
    }
}


# Make this unique, and don't share it with anybody.
SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'


ADMINS = (
    ('Webmaster', 'webmaster@localhost'),
)
MANAGERS = ADMINS

EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
SERVER_EMAIL = 'django@erdbebendienst.de'
DEFAULT_FROM_EMAIL = 'noreply@erdbebendienst.de'
