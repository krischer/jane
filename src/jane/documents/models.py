# -*- coding: utf-8 -*-
"""
Models for the document database of Jane.

The hierarchy is fairly simple:

* There are different types of documents stored in the ``DocumentType`` model.
* Each document type can have various documents stored in the ``Document``
  model.
* Each document can have multiple indices, each stored in a
  ``DocumentIndex`` model
* Each index can have multiple attachments, each stored in a
  ``DocumentIndexAttachment`` model.


New document types can be defined by adding new plug-ins.
"""
from django.conf import settings
from django.contrib.gis.db import models
from django.shortcuts import get_object_or_404
from djangoplugins.fields import PluginField, ManyPluginField
from jsonfield.fields import JSONField

from rest_framework import status

import hashlib

from jane.documents import plugins
from jane.exceptions import (JaneDocumentAlreadyExists,
                             JaneNotAuthorizedException)


class PostgreSQLJSONBField(JSONField):
    """
    Make the JSONField use JSONB as a datatype, a typed JSON variant.
    """
    def db_type(self, connection):
        return "jsonb"


class DocumentType(models.Model):
    """
    Document category. Will be determined from the registered plugins.
    """
    name = models.SlugField(max_length=20, primary_key=True)
    # Plugins for this document type.
    definition = PluginField(plugins.DocumentPluginPoint,
                             related_name="definition")
    # Each document type must have exactly one indexer.
    indexer = PluginField(plugins.IndexerPluginPoint, related_name='indexer')
    # It can have any number of validators. It is strongly recommended to
    # provide at least one.
    validators = ManyPluginField(plugins.ValidatorPluginPoint, blank=True,
                                 related_name='validators')
    # Custom permissions upon retrieving data.
    retrieve_permissions = ManyPluginField(
        plugins.RetrievePermissionPluginPoint, blank=True,
        related_name='retrieve_permissions')
    # Same for uploading documents.
    upload_permissions = ManyPluginField(
        plugins.UploadPermissionPluginPoint, blank=True,
        related_name='upload_permissions')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Document Type'
        verbose_name_plural = 'Document Types'


class _DocumentManager(models.Manager):
    def delete_document(self, document_type, name, user):
        """
        For convenience reasons, offer that method here, including
        authentication.

        :param document_type: The document type either as a
            jane.documents.models.DocumentType instance or as a string.
        :param name: The name of the resource. If it exists, it will be
            deleted.
        :param user: The user object responsible for the action. Must be
            passed to ensure a consistent handling of permissions.
        """
        # Works with strings and DocumentType instances.
        if not isinstance(document_type, DocumentType):
            document_type = get_object_or_404(
                DocumentType, name=document_type)
        document_type_str = document_type.name

        # The user in question must have the permission to modify documents
        # of that type.
        if not user.has_perm(
                        "documents.can_modify_%s" % document_type_str):
            raise JaneNotAuthorizedException(
                "No permission to delete documents of that type")

        obj = get_object_or_404(Document, document_type=document_type,
                                name=name)
        obj.delete()

    def add_or_modify_document(self, document_type, name, data, user):
        """
        Add a new or modify an existing document.

        Use this method everywhere to ensure a consistent handling of the
        permissions. A user object has to be passed for this purpose.

        :param document_type: The document type either as a
            jane.documents.models.DocumentType instance or as a string.
        :param name: The name of the resource. If it exists, it will be
            updated, otherwise a new one will be created.
        :param data: The data as a byte string.
        :param user: The user object responsible for the action. Must be
            passed to ensure a consistent handling of permissions.
        """
        # Works with strings and DocumentType instances.
        if not isinstance(document_type, DocumentType):
            document_type = get_object_or_404(
                DocumentType, name=document_type)
        document_type_str = document_type.name

        # The user in question must have the permission to modify documents
        # of that type.
        if not user.has_perm(
                        "documents.can_modify_%s" % document_type_str):
            raise JaneNotAuthorizedException(
                "No permission to upload documents of that type")

        # Calculate the hash upfront to not upload any duplicates.
        sha1 = hashlib.sha1(data).hexdigest()
        if Document.objects.filter(sha1=sha1).exists():
            raise JaneDocumentAlreadyExists("Data already exists in the "
                                            "database.")

        try:
            document = Document.objects.get(
                document_type=document_type, name=name)
            document.modified_by = user
            stat = status.HTTP_204_NO_CONTENT
        except Document.DoesNotExist:
            document = Document(
                document_type=document_type,
                name=name,
                modified_by=user,
                created_by=user)
            stat = status.HTTP_201_CREATED

        document.data = data

        document.save()

        # Return the status to be able to generate good HTTP responses. Can
        # be ignored if not needed.
        return stat


class Document(models.Model):
    """
    A document of a particular type.

    Each document within Jane's document database is essentially a file of
    any type that is described by indices.
    """
    # The type of the document. Depends on the available Jane plug-ins.
    document_type = models.ForeignKey(DocumentType, related_name='documents')
    # The name of that particular document. Oftentimes the filename. Unique
    # together with the document type to enable a nice REST API.
    name = models.SlugField(max_length=255, db_index=True)
    # The content type of the data. Must be given to be able to provide a
    # reasonable HTTP view of the data.
    content_type = models.CharField(max_length=255)
    # The actual data as a binary field.
    data = models.BinaryField(editable=False)
    # The file's size in bytes.
    filesize = models.IntegerField(editable=False)
    # sha1 hash of the data to avoid duplicates.
    sha1 = models.CharField(max_length=40, db_index=True, unique=True,
                            editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    # Users responsible for the aforementioned actions.
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   related_name='documents_created')
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    related_name='documents_modified')
    objects = _DocumentManager()

    def __str__(self):
        return "Document of type '%s', name: %s" % (self.document_type,
                                                    self.name)

    class Meta:
        ordering = ['pk']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        unique_together = ['document_type', 'name']


class _DocumentIndexManager(models.GeoManager):
    """
    Custom queryset manager for the document indices.
    """
    JSON_QUERY_TEMPLATE_MAP = {
        "int": "CAST(json->>'%s' AS INTEGER) %s %s",
        "float": "CAST(json->>'%s' AS REAL) %s %s",
        "str": "LOWER(json->>'%s') %s LOWER('%s')",
        "bool": "CAST(json->>'%s' AS BOOL) %s %s",
        "UTCDateTime": "CAST(json->>'%s' AS TIMESTAMP) %s TIMESTAMP '%s'"
    }

    def _get_json_query(self, key, operator, type, value):
        return self.JSON_QUERY_TEMPLATE_MAP[type] % (key, operator, str(value))

    def get_filtered_queryset(self, document_type, queryset=None,
                              **kwargs):
        """
        Returns a queryset filtered on the items in the JSON document.

        :param document_type: The document type to query. Will be ignored if a
            queryset is passed.
        :param queryset: If no queryset is passed, a new one will be
            created, otherwise an existing one will be used and filtered.
        :param kwargs: Any additional query parameters.

        Assuming a key named ``"example"`` in the JSON file you can search
        for:

        * Equality with ``get_filtered_queryset("ex", example=1)``
          (Potentially with wildcards for strings)
        * Inequality with ``get_filtered_queryset(
            "ex", kwargs={"!example": 1})``
          (Potentially with wildcards for strings). Exclamation marks are
          not valid identifiers, thus a kwargs dict  has to be used.
        * Larger or equal (``>=``) or smaller or equal (``<=``) with
          ``get_filtered_queryset("ex", min_example=1)`` or
          ``get_filtered_queryset("ex", max_example=1)``, respectively.

        The available operations and search parameters depend on the type::

        * String can have wildcards for (in)equality searches:
            ``author=ja*``
            ``!author=?test``
        * Ints/Floats can either be searched for (in)equality (these
          naturally are very fragile for floating point numbers):
            ``magnitude=7.2``
            ``!count=0``
          or minimum and maximum values:
            ``min_magnitude=5, max_magnitude=7``
        * Same for ``obspy.UTCDateTime`` objects:
            ``origin_time=obspy.UTCDateTime("2012-01-02")``
            `...&min_origin_time=2012-01-02&max_origin_time=2013-01-01&...`
        * Booleans can only be searched for (in)equality.
            ``public=True``
            ``kwargs={"!public": True}``

        Please note that as soon as you search for a value, all values that
        are null will be discarded from the queryset (even if you search for
        !=)! This might be changed in the future.
        """
        from obspy import UTCDateTime

        res_type = get_object_or_404(DocumentType, name=document_type)

        # Only create if necessary.
        if queryset is None:
            queryset = DocumentIndex.objects.\
                filter(document__document_type=res_type)

        # The REST API is fairly excessive with nested lookups. Prefetch
        # most of them which greatly speeds up everything.
        # prefetch_related() does the join in Python which is slower but
        # works with many-to-many fields. Select related is faster but only
        # works with foreign keys.
        queryset = queryset\
            .prefetch_related('attachments')\
            .select_related('document', 'document__document_type')

        # Nothing to do.
        if not kwargs:
            return queryset

        meta = res_type.indexer.get_plugin().meta

        type_map = {
            "str": str,
            "float": float,
            "int": int,
            "bool": bool,
            "UTCDateTime": UTCDateTime
        }

        # Filter based on the attributes in the meta field.
        where = []

        for key, value_type in meta.items():
            # Handle strings.
            if value_type == "str":
                # Strings can be searched on wildcarded (in)equalities
                choices = (("%s", "="), ("!%s", "!="))
                for name, operator in choices:
                    name = name % key
                    if name not in kwargs:
                        continue
                    value = kwargs[name]
                    # Possible wildcards.
                    if "*" in value or "?" in value:
                        value = value.replace("?", "_").replace("*", r"%%")
                        # PostgreSQL specific case insensitive LIKE statement.
                        if operator == "=":
                            where.append("json->>'%s' ILIKE '%s'" % (key,
                                                                     value))
                        elif operator == "!=":
                            where.append("json->>'%s' NOT ILIKE '%s'" % (
                                key, value))
                        else:
                            raise NotImplementedError
                    else:
                        where.append(
                            self._get_json_query(key, operator, value_type,
                                                 value))
            # Handle integers, floats, and UTCDateTimes.
            elif value_type in ("int", "float", "UTCDateTime"):
                choices = (("min_%s", ">="), ("max_%s", "<="), ("%s", "="),
                           ("!%s", "!="))
                for name, operator in choices:
                    name = name % key
                    if name not in kwargs:
                        continue
                    where.append(self._get_json_query(
                        key, operator, value_type,
                        type_map[value_type](kwargs[name])))
            # Handle bools.
            elif value_type == "bool":
                # Booleans can be searched for (in)equality.
                choices = (("%s", "="), ("!%s", "!="))
                for name, operator in choices:
                    name = name % key
                    if name not in kwargs:
                        continue
                    value = str(kwargs[name]).lower()
                    if value in ["t", "true", "yes", "y"]:
                        value = "true"
                    elif value in ["f", "false", "no", "n"]:
                        value = "false"
                    else:
                        raise NotImplementedError
                    where.append(self._get_json_query(
                        key, operator, value_type, value))
            else:
                raise NotImplementedError

        queryset = queryset.extra(where=where)
        return queryset


class DocumentIndex(models.Model):
    """
    Indexed values for a specific document.
    """
    document = models.ForeignKey(Document, related_name='indices')
    json = PostgreSQLJSONBField(verbose_name="JSON")
    geometry = models.GeometryCollectionField(blank=True, null=True,
                                              geography=True)

    objects = _DocumentIndexManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Index'
        verbose_name_plural = 'Indices'

    def __str__(self):
        return str(self.json)


class _DocumentIndexAttachmentManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        # Usernames are always looked up for the REST API. This is much
        # quicker.
        queryset = super()\
            .get_queryset(*args, **kwargs)\
            .select_related("created_by", "modified_by")
        return queryset

    def delete_attachment(self, document_type, pk, user):
        """
        For convenience reasons, offer that method here, including
        authentication.

        :param document_type: The document type either as a
            jane.documents.models.DocumentType instance or as a string.
        :param pk: The primary key of the attachment.
        :param user: The user object responsible for the action. Must be
            passed to ensure a consistent handling of permissions.
        """
        # Works with strings and DocumentType instances.
        if not isinstance(document_type, DocumentType):
            document_type = get_object_or_404(
                DocumentType, name=document_type)
        document_type_str = document_type.name

        # The user in question must have the permission to modify
        # attachments for documents of that type.
        if not user.has_perm("documents.can_modify_%s_attachments" %
                             document_type_str):
            raise JaneNotAuthorizedException(
                "No permission to delete attachments for documents of that "
                "type")

        obj = get_object_or_404(DocumentIndexAttachment, pk=pk)
        obj.delete()

    def add_or_modify_attachment(self, document_type, index_id,
                                 content_type, category,
                                 data, user, pk=None):
        """
        Add a new or modify an existing attachment.

        Use this method everywhere to ensure a consistent handling of the
        permissions. A user object has to be passed for this purpose.

        :param document_type: The document type either as a
            jane.documents.models.DocumentType instance or as a string.
        :param index_id: The id of the document index this attachment is for.
        :param content_type: The content type of the attachment as a string.
        :param category: The category of the attachment (the tag) as a string.
        :param data: The data as a byte string.
        :param user: The user object responsible for the action. Must be
            passed to ensure a consistent handling of permissions.
        :param pk: The primary key of the attachment. If given, an existing
            one will modified, if not, a new one will be created.
        """
        if pk is None:
            method = "create"
        else:
            method = "update"

        # Works with strings and DocumentType instances.
        if not isinstance(document_type, DocumentType):
            document_type = get_object_or_404(
                DocumentType, name=document_type)
        document_type_str = document_type.name

        # The user in question must have the permission to modify documents
        # of that type.
        if not user.has_perm(
                        "documents.can_modify_%s" % document_type_str):
            raise JaneNotAuthorizedException(
                "No permission to %s attachments for documents of that type."
                % method)

        index = get_object_or_404(DocumentIndex, pk=index_id)

        if method == "update":
            attachment = get_object_or_404(DocumentIndexAttachment, pk=pk,
                                           index=index)
            stat = status.HTTP_204_NO_CONTENT
        else:
            attachment = DocumentIndexAttachment(
                index=index,
                created_by=user
            )
            stat = status.HTTP_201_CREATED

        attachment.category = category
        attachment.content_type = content_type
        attachment.modified_by = user
        attachment.data = data

        attachment.save()

        # Return the status to be able to generate good HTTP responses. Can
        # be ignored if not needed.
        return stat


class DocumentIndexAttachment(models.Model):
    """
    Attachments for one Document.
    """
    index = models.ForeignKey(DocumentIndex, related_name='attachments')
    category = models.SlugField(max_length=20, db_index=True)
    content_type = models.CharField(max_length=255)
    data = models.BinaryField()
    # Attachments are almost independent from Documents thus they should
    # have people responsible for them.
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    # Users responsible for the aforementioned actions.
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   related_name='attachments_created')
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    related_name='attachments_modified')
    objects = _DocumentIndexAttachmentManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'

    def __str__(self):
        return str(self.data)
