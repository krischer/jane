# -*- coding: utf-8 -*-

import os

from django.core.management.base import BaseCommand

from jane.documents import models


class Command(BaseCommand):
    args = 'resourcetype path'
    help = "Upload documents"  # @ReservedAssignment

    def handle(self, *args, **kwargs):
        # resource type
        try:
            resource_type = models.ResourceType.objects.get(name=args[0])
        except:
            raise Exception('Valid resource type required')
        # path
        try:
            path = args[1]
            if not os.path.isdir(path):
                raise
        except:
            path = os.path.curdir
        # upload
        