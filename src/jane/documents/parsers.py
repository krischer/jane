# -*- coding: utf-8 -*-
from rest_framework.parsers import BaseParser


class JaneDocumentUploadParser(BaseParser):
    media_type = "*/*"

    def parse(self, stream, media_type=None, parser_context=None):
        return stream
