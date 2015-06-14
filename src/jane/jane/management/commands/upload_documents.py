# -*- coding: utf-8 -*-
import glob
import io
import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from jane.documents import models


class Command(BaseCommand):
    help = "Upload documents to Jane's document database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--user', type=str,
            choices=[_i.username for _i in get_user_model().objects.all()],
            help='Upload documents in the name of this user.',
            required=True)
        parser.add_argument(
            'document_type', type=str,
            choices=[_i.name for _i in models.DocumentType.objects.all()],
            help='The document type of the files to upload.')
        parser.add_argument(
            'path', type=str, nargs='+',
            help='The files to upload.')

    def handle(self, *args, **kwargs):
        # Cannot easily fail as the model type settings are enforced by
        # argparse.
        document_type = models.DocumentType.objects.get(
            name=kwargs["document_type"])

        user = get_user_model().objects.get(username=kwargs["user"])

        paths = kwargs["path"]
        all_files = []
        for pattern in paths:
            all_files.extend(glob.glob(pattern))

        for filename in all_files:
            print('Uploading %s...' % filename)
            with open(filename, "rb") as fh:
                with io.BytesIO(fh.read()) as data:
                    document = models.Document(
                        document_type=document_type,
                        name=os.path.basename(filename),
                        data=data.read(),
                        created_by=user,
                        modified_by=user
                    )
                    try:
                        document.save()
                    except Exception as e:
                        print("Failed uploading due to: %s" % str(e))
