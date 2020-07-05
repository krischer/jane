# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from jane.documents import models, signals


class Command(BaseCommand):
    help = "Reindex all documents in Jane's document database."

    def add_arguments(self, parser):
        parser.add_argument(
            'document_type', type=str,
            choices=[_i.name for _i in models.DocumentType.objects.all()],
            help='The document type of the files to upload.')

    def handle(self, *args, **kwargs):
        # Cannot easily fail as the model type settings are enforced by
        # argparse.
        document_type = models.DocumentType.objects.get(
            name=kwargs["document_type"])

        for doc in models.Document.objects.filter(document_type=document_type):
            signals.index_document(sender=None, instance=doc, created=None)
            print('.', end='')
