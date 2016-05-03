# -*- coding: utf-8 -*-

from django.conf.urls import include, url
from rest_framework.urlpatterns import format_suffix_patterns

from jane.jane import views


urlpatterns = [
    url(r'^$',
        view=views.index,
        name='jane_index'),
    url(r'^rest/?$',
        view=views.rest_root,
        name='rest_root'),
    url(r'^rest/current_user/$',
        view=views.current_user,
        name='current_user'),
    url(r'^rest/api-auth/',
        include('rest_framework.urls', namespace='rest_framework'))
]

urlpatterns = format_suffix_patterns(urlpatterns)
