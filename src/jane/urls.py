# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import include, url, static
from django.contrib.gis import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


admin.autodiscover()


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('jane.waveforms.urls')),
    url(r'', include('jane.documents.urls')),
    url(r'', include('jane.jane.urls')),
    url(r'^fdsnws/', include('jane.fdsnws.urls')),
]


if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', static.serve,
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
        url(r'', include('django.contrib.staticfiles.urls')),
    ]
    urlpatterns += staticfiles_urlpatterns()
