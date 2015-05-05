# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models, views


@api_view(['GET'])
def rest_root(request, format=None):
    """
    The root of the Jane's REST interface. Lists all registered
    document document types + the waveform type.
    """
    if request.method == "GET":
        resource_types = models.DocumentType.objects.all()
        data = {
            _i.name: reverse(views.record_list, args=[_i.name],
                             request=request)
            for _i in resource_types
        }
        # manually add waveforms into our REST root
        # data['documents'] = reverse('rest_documents-list', request=request)
        data["documents"] = reverse(views.documents_rest_root, request=request)
        data['waveforms'] = reverse('rest_waveforms-list', request=request)
        return Response([{'name': i[0], 'url': i[1]}
                         for i in sorted(data.items())])


def index(request):
    options = {
        'host': request.build_absolute_uri('/')[:-1],
        }
    return render_to_response("index.html", options,
                              RequestContext(request))
