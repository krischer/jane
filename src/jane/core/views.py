# -*- coding: utf-8 -*-
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models
from jane.documents.views import indexed_values_list


@api_view(['GET'])
def rest_root(request, format=None):  # @ReservedAssignment
    """
    The root of the jane REST interface. Lists all registered
    document resource types and the waveform type.
    """
    if request.method == "GET":
        resource_types = models.ResourceType.objects.order_by('name')
        data = {
           _i.name: reverse(indexed_values_list, args=[_i.name],
                            request=request)
           for _i in resource_types
        }
        data['waveforms'] = 'http://localhost:8000/rest/waveforms'
        return Response(data)
