# -*- coding: utf-8 -*-

import glob
import hashlib
import io
import os
import warnings

from django.core.management.base import BaseCommand

from jane.documents import models


class Command(BaseCommand):
    args = 'document_type path path path'
    help = "Upload documents"  # @ReservedAssignment

    def handle(self, *args, **kwargs):  # @UnusedVariable
        if len(args) < 2:
            raise ValueError("document_type and path are required")

        # document type
        try:
            document_type = models.DocumentType.objects.get(name=args[0])
        except:
            raise ValueError('Valid document type required')

        # path(s)
        paths = args[1:]

        all_files = []
        for pattern in paths:
            all_files.extend(glob.glob(pattern))

        for filename in all_files:
            print(filename)
            with open(filename, "rb") as fh:
                data = io.BytesIO(fh.read())

            sha1 = hashlib.sha1(data.read()).hexdigest()

            qs = models.DocumentRevision.objects.filter(sha1=sha1).exists()
            if qs is True:
                msg = "File '%s' already exists in the database."
                warnings.warn(msg % filename)
                continue

            data.seek(0, 0)

            document = models.Document(document_type=document_type)
            document.save()

            document = models.DocumentRevision(
                document=document,
                revision_number=1,
                filename=os.path.abspath(filename),
                data=data.read(),
                filesize=os.path.getsize(filename),
                sha1=sha1
            )
            document.save()
