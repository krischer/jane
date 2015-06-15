# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from rest_framework.urlpatterns import format_suffix_patterns

from jane.documents import views
from jane.jane.utils import OptionalTrailingSlashSimpleRouter


urlpatterns = [
    # This view just returns the data of a document. Its thus a bit "hidden".
    url(r'^rest/__document_data__/(?P<pk>[0-9]+)$', views.document_data,
        name="document_data"),
    # Root url for the documents.
    url(r'^rest/documents/?$', views.documents_rest_root),
    # Root url for the indices.
    url(r'^rest/document_indices/?$', views.documents_indices_rest_root),

    # url(r'^rest/(?P<document_type>\w+)/$', views.record_list),
    # url(r'^rest/(?P<document_type>\w+)/(?P<pk>[0-9]+)/$',
    #     views.record_detail),
    # url(r'^rest/(?P<document_type>\w+)/(?P<index_id>[0-9]+)/'
    #     '(?P<attachment_id>[0-9]+)/$',
    #     views.attachment_detail)
]
urlpatterns = format_suffix_patterns(urlpatterns)


# Route documents and document indices.
router = OptionalTrailingSlashSimpleRouter(trailing_slash=False)
router.register(prefix='documents/(?P<document_type>[a-zA-Z0-9]+)',
                viewset=views.DocumentsView,
                base_name="rest_documents")
router.register(prefix='document_indices/(?P<document_type>[a-zA-Z0-9]+)',
                viewset=views.DocumentIndicesView,
                base_name="rest_document_indices")
urlpatterns.append(url(r'^rest/', include(router.urls)))


from .plugins import initialize_plugins
available_plugins = initialize_plugins()
