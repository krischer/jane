# -*- coding: utf-8 -*-
from collections import OrderedDict

from django.conf import settings
from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

import jane
from jane.documents import models, views
from jane.waveforms.models import ContinuousTrace

from .serializer import UserSerializer


@api_view(['GET'])
def rest_root(request, format=None):
    """
    The root of Jane's REST interface. From here you have access to three
    subsections:

    **/waveforms**
    <div style="margin-left: 50px; margin-right: 50px;">
    *Browseable read-only REST API to explore the waveform database of Jane
    on a per waveform trace basis. Likely of limited usability but maybe
    interesting for some use cases. Each resource maps to one trace
    including a plot and some meta information.*
    </div>

    **/documents**
    <div style="margin-left: 50px; margin-right: 50px;">
    *REST API to work with Jane's document database at the document level.
    You can browse the available documents and view its associated indices.
    It is furthermore possible to add new documents via ``PUT`` or delete
    documents including all indices and attachments with ``DELETE``. Indices
    are generated automatically upon uploading or modifying a document.*
    </div>

    **/document_indices**
    <div style="margin-left: 50px; margin-right: 50px;">
    *REST API to work with Jane's document database at the index level. Each
    REST resource is one index which can also be searched upon. You can
    furthermore add, modify, or delete attachments for each index with
    ``PUT`` or ``DELETE``. One cannot delete or modify individual indices
    as they are tied to a document. To add, modify, or delete a whole
    document including all associated indices and attachments, please work
    with the **/documents** endpoint.*
    </div>
    """
    if request.method == "GET":
        # Use OrderedDicts to force the order of keys. Is there a different
        # way to do this within DRF?
        waveforms = OrderedDict()
        waveforms["name"] = "waveforms"
        waveforms["url"] = reverse('rest_waveforms-list', request=request)
        waveforms["description"] = ("REST view of Jane's waveform database")
        waveforms["available_traces"] = ContinuousTrace.objects.count()

        documents = OrderedDict()
        documents["name"] = "documents"
        documents["url"] = reverse(views.documents_rest_root, request=request)
        documents["description"] = ("Jane's document database at the "
                                    "document level")
        documents["available_documents"] = models.Document.objects.count()

        document_indices = OrderedDict()
        document_indices["name"] = "document_indices"
        document_indices["url"] = reverse(views.documents_indices_rest_root,
                                          request=request)
        document_indices["description"] = (
            "Jane's document database at the index level")
        document_indices["available_indices"] = \
            models.DocumentIndex.objects.count()

        return Response([waveforms, documents, document_indices])


@api_view(['GET'])
def current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


def index(request):
    context = {
        'instance_name': settings.JANE_INSTANCE_NAME,
        'accent_color': settings.JANE_ACCENT_COLOR,
        'version': jane.__version__
    }
    return render(request, "jane/index.html", context)
