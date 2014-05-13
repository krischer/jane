# -*- coding: utf-8 -*-
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models
from jane.documents.views import indexed_values_list

from collections import OrderedDict


@api_view(['GET'])
def rest_root(request, format=None):  # @ReservedAssignment
    """
    The root of the jane REST interface. Lists all registered
    document resource types + the waveform type.
    """
    if request.method == "GET":
        resource_types = models.ResourceType.objects.order_by('name')
        data = {
           _i.name: reverse(indexed_values_list, args=[_i.name],
                            request=request)
           for _i in resource_types
        }
        # manually add waveforms into our REST root
        data['waveforms'] = reverse('waveforms-list', request=request)

        ordered_data = OrderedDict()
        for key in sorted(data.keys()):
            ordered_data[key] = data[key]

        return Response(ordered_data)
