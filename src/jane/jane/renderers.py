# -*- coding: utf-8 -*-
from django.conf import settings
from rest_framework.renderers import BrowsableAPIRenderer


class JaneBrowsableAPIRenderer(BrowsableAPIRenderer):
    """
    Custom API renderer mainly used to change the context passed to the
    template.
    """
    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)

        context['instance_name'] = settings.JANE_INSTANCE_NAME
        context['accent_color'] = settings.JANE_ACCENT_COLOR
        return context
