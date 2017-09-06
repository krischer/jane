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
import hashlib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.gis.db import models
from django.contrib.gis.measure import Distance
from django.contrib.postgres.fields import jsonb
from django.core.urlresolvers import reverse
from django.db import connection
from django.db.models.aggregates import Count
from django.db.models.expressions import OrderBy, RawSQL
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import filesizeformat
from djangoplugins.fields import PluginField, ManyPluginField
from obspy.core.utcdatetime import UTCDateTime
from rest_framework import status

from jane.documents import plugins, signals
from jane.documents.utils import deg2km
from jane.exceptions import (JaneDocumentAlreadyExists,
                             JaneNotAuthorizedException)


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


class DocumentManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        # defer data
        queryset = queryset.defer('data')
        return queryset

    def get_filtered_queryset(self, document_type, queryset=None, negate=False,
                              **kwargs):
        """
        Returns a queryset filtered on the items in the JSON index field.

        For all args/kwargs see
        :meth:`DocumentIndexManager.+get_filtered_queryset`.
        """
        # Only create if necessary.
        if queryset is None:
            queryset = Document.objects

        # filter by document type
        res_type = get_object_or_404(DocumentType, name=document_type)
        queryset = queryset.filter(document_type=res_type)

        # Nothing to do.
        if not kwargs:
            return queryset

        # now do the respective filtering on the document indices and get
        # a list of document ids that match
        # XXX not sure if this is safe, need to check what happens if database
        # XXX gets changed while evaluating the request (e.g. table row gets
        # XXX deleted during request == ids of rows change??)
        indices_queryset = DocumentIndex.objects.get_filtered_queryset(
            document_type=document_type, queryset=None, negate=negate,
            **kwargs)

        # XXX TODO this does not cover the case of multiple indices for one
        # XXX TODO single document yet!
        document_indices = [doc_ind.document.id
                            for doc_ind in indices_queryset]

        # now restrict document query to respective document ids
        queryset = queryset.filter(id__in=document_indices)

        return queryset

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
    name = models.CharField(max_length=255, db_index=True)
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
    objects = DocumentManager()

    class Meta:
        ordering = ['id']
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        unique_together = ['document_type', 'name']

    def __str__(self):
        return str(self.id)

    def verbose_name(self):
        return "Document of type '%s', name: %s" % (self.document_type,
                                                    self.name)

    def format_document_type(self):
        return self.document_type.name
    format_document_type.short_description = 'Document type'
    format_document_type.admin_order_field = 'document_type__name'

    def format_filesize(self):
        return filesizeformat(self.filesize)
    format_filesize.short_description = 'File size'
    format_filesize.admin_order_field = 'filesize'

    def save(self, *args, **kwargs):
        """
        Manually trigger the signals as they are for some reason unreliable
        and for example do not get called when a model is updated.
        """
        signals.validate_document(sender=None, instance=self)
        signals.set_document_metadata(sender=None, instance=self)
        super().save(*args, **kwargs)
        signals.index_document(sender=None, instance=self, created=None)


class DocumentIndexManager(models.GeoManager):
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

    JSON_ORDERING_TEMPLATE = {
        "int": "CAST(json->>'%s' AS INTEGER)",
        "float": "CAST(json->>'%s' AS REAL)",
        "str": "json->>'%s'",
        "bool": "CAST(json->>'%s' AS BOOL)",
        "UTCDateTime": "CAST(json->>'%s' AS TIMESTAMP)"
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        # improve query performance for foreignkeys
        queryset = queryset.\
            select_related('document', 'document__document_type')
        # defer data
        queryset = queryset.defer('document__data')
        # annotate number of attachments
        queryset = queryset.\
            annotate(attachments_count=Count('attachments'))
        return queryset

    def _get_json_query(self, key, operator, type, value):
        return self.JSON_QUERY_TEMPLATE_MAP[type] % (key, operator, str(value))

    def apply_retrieve_permission(self, document_type, queryset, user):
        """
        Apply potential additional restrictions based on the permissions.
        """
        retrieve_permissions = document_type.retrieve_permissions.all()

        if user is None:
            user = AnonymousUser()

        if retrieve_permissions:
            for perm in retrieve_permissions:
                perm = perm.get_plugin()
                app_label = DocumentType._meta.app_label
                perm_name = "%s.%s" % (app_label, perm.permission_codename)
                if user.has_perm(perm_name):
                    queryset = perm.filter_queryset_user_has_permission(
                        queryset, model_type="index", user=user)
                else:
                    queryset = \
                        perm.filter_queryset_user_does_not_have_permission(
                            queryset=queryset, model_type="index", user=user)
        return queryset

    def get_distinct_values(self, document_type, json_key):
        """
        Get distinct values for a certain field in the JSON document.
        """
        res_type = get_object_or_404(DocumentType, name=document_type)
        meta = res_type.indexer.get_plugin().meta
        if json_key not in meta:
            raise Http404("Key '%s' not in the meta attribute of the '%s' "
                          "resource type." % (json_key, document_type))

        if meta[json_key] != "str":
            raise Http404("Currently only implemented for string index keys")

        # XXX: I am not sure how to formulate this within Django's ORM...
        # Should be a safe enough query especially with the checks above but
        # one might still want to change it.

        cursor = connection.cursor()
        cursor.execute("""
            SELECT DISTINCT
            documents_documentindex.json->>%s
            FROM documents_documentindex
            INNER JOIN "documents_document"
            ON ( "documents_documentindex"."document_id" =
                 "documents_document"."id" )
            WHERE ("documents_document"."document_type_id" = %s)
        """, [json_key, document_type])

        return [_i[0] for _i in cursor.fetchall()]

    def get_filtered_queryset_radial_distance(
            self, document_type, central_latitude, central_longitude,
            min_radius=None, max_radius=None, queryset=None, user=None):
        """
        Filter a dataset to get all indices within a certain distance to a
        point.

        Useful for the radial queries at the FDSN station and event service.

        :param document_type: The document type to query. Will be ignored if a
            queryset is passed.
        :param central_latitude: The latitude of the central point.
        :param central_longitude: The longitude of the central point.
        :param min_radius: The minimum radius from the central point in degree.
        :param max_radius: The maximum radius from the central point in degree.
        :param queryset: If no queryset is passed, a new one will be
            created, otherwise an existing one will be used and filtered.
        """
        # Only create if necessary.
        if queryset is None:
            queryset = DocumentIndex.objects

        # filter by document type
        res_type = get_object_or_404(DocumentType, name=document_type)
        queryset = queryset.filter(document__document_type=res_type)

        queryset = self.apply_retrieve_permission(document_type=res_type,
                                                  queryset=queryset,
                                                  user=user)

        central_point = 'POINT({lng} {lat})'.format(lng=central_longitude,
                                                    lat=central_latitude)
        if min_radius is not None:
            queryset = queryset.filter(
                geometry__distance_gt=(central_point,
                                       Distance(km=deg2km(min_radius))))
        if max_radius is not None:
            queryset = queryset.filter(
                geometry__distance_lt=(central_point,
                                       Distance(km=deg2km(max_radius))))
        return queryset

    def get_filtered_queryset(self, document_type, queryset=None, user=None,
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
        # Only create if necessary.
        if queryset is None:
            queryset = DocumentIndex.objects

        # filter by document type
        res_type = get_object_or_404(DocumentType, name=document_type)
        queryset = queryset.filter(document__document_type=res_type)

        queryset = self.apply_retrieve_permission(document_type=res_type,
                                                  queryset=queryset,
                                                  user=user)

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
                            raise NotImplementedError()  # pragma: no cover
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
                        raise NotImplementedError()  # pragma: no cover
                    where.append(self._get_json_query(
                        key, operator, value_type, value))
            else:
                raise NotImplementedError()  # pragma: no cover

        queryset = queryset.extra(where=where)

        if "ordering" in kwargs and kwargs["ordering"] in meta:
            ord = kwargs["ordering"]
            queryset = queryset.order_by(
                OrderBy(
                    RawSQL(self.JSON_ORDERING_TEMPLATE[meta[ord]] % ord, [])))
        return queryset


class DocumentIndex(models.Model):
    """
    Indexed values for a specific document.
    """
    document = models.ForeignKey(Document, related_name='indices')
    json = jsonb.JSONField(verbose_name="JSON")
    geometry = models.GeometryCollectionField(blank=True, null=True,
                                              geography=True)

    objects = DocumentIndexManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Index'
        verbose_name_plural = 'Indices'

    def __str__(self):
        return str(self.id)

    def verbose_name(self):
        return str(self.json)

    def format_document_type(self):
        return self.document.document_type.name
    format_document_type.short_description = 'Document type'
    format_document_type.admin_order_field = 'document__document_type__name'

    def format_document_id(self):
        if self.document.id is None:
            return
        url = reverse('admin:%s_%s_change' % (self._meta.app_label,
                                              self._meta.object_name.lower()),
                      args=[self.document.id])
        return "<a href='%s'>%d</a>" % (url, self.document.id)
    format_document_id.allow_tags = True
    format_document_id.short_description = 'Document ID'
    format_document_id.admin_order_field = 'document__id'

    def format_index_id(self):
        if self.id is None:
            return
        url = reverse('admin:%s_%s_change' % (self._meta.app_label,
                                              self._meta.object_name.lower()),
                      args=[self.id])
        return "<a href='%s'>%d</a>" % (url, self.id)
    format_index_id.allow_tags = True
    format_index_id.short_description = 'Index ID'


class DocumentIndexAttachmentManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        # improve query performance for foreignkeys
        queryset = queryset.\
            select_related("created_by", "modified_by")
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
                "documents.can_modify_%s_attachments" % document_type_str):
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
    category = models.CharField(max_length=50, db_index=True)
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
    objects = DocumentIndexAttachmentManager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'

    def __str__(self):
        return str(self.id)

    def verbose_name(self):
        return str(self.data)

    def format_attachment_id(self):
        if self.id is None:
            return
        url = reverse('admin:%s_%s_change' % (self._meta.app_label,
                                              self._meta.object_name.lower()),
                      args=[self.id])
        return "<a href='%s'>%d</a>" % (url, self.id)
    format_attachment_id.allow_tags = True
    format_attachment_id.short_description = 'Attachment ID'

    def format_filesize(self):
        return filesizeformat(len(self.data))
    format_filesize.short_description = 'File size'
    format_filesize.admin_order_field = 'filesize'
