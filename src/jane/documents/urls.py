# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from rest_framework.urlpatterns import format_suffix_patterns

from jane.documents import views
from jane.jane.utils import OptionalTrailingSlashSimpleRouter


urlpatterns = [
    url(r'^rest/documents/?$', views.documents_rest_root),
    url(r'^rest/(?P<document_type>\w+)/$', views.record_list),
    url(r'^rest/(?P<document_type>\w+)/(?P<pk>[0-9]+)/$',
        views.record_detail),
    url(r'^rest/(?P<document_type>\w+)/(?P<index_id>[0-9]+)/'
        '(?P<attachment_id>[0-9]+)/$',
        views.attachment_detail),
    url(r'^rest/(?P<pk>[0-9]+)/data/$', views.document_data),
]
urlpatterns = format_suffix_patterns(urlpatterns)


for name, viewset in views.document_viewsets.items():
    router = OptionalTrailingSlashSimpleRouter(trailing_slash=False)
    router.register(name, viewset, base_name="rest_documents_%s" % name)

    urlpatterns.append(url(r'^rest/documents/', include(router.urls)))


from .plugins import initialize_plugins
available_plugins = initialize_plugins()
