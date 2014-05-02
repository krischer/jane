# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext

from jane.documents import models


def test(request, resource_type):
    """
    """
    resource_type = get_object_or_404(models.ResourceType, name=resource_type)
    values = models.IndexedValue.objects.\
        filter(revision__resource__resource_type=resource_type).\
        extra(where=["json->>'muh' = 'kuh'"])

    return render_to_response('documents/test.html',
        {'values': values},
        context_instance=RequestContext(request))
