# -*- coding: utf-8 -*-

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

from jane.documents import models


@api_view(['GET'])
def rest_root(request, format=None):  # @ReservedAssignment
    """
    The root of the jane REST interface. Lists all registered
    document resource types + the waveform type.
    """
    if request.method == "GET":
        resource_types = models.ResourceType.objects.all()
        data = {
           _i.name: reverse('record_list', args=[_i.name],
                            request=request)
           for _i in resource_types
        }
        # manually add waveforms into our REST root
        data['waveforms'] = reverse('rest_waveforms-list', request=request)
        return Response([{'name': i[0], 'url': i[1]}
                         for i in sorted(data.items())])
