
import os
try:
    import json
except ImportError:
    import simplejson as json

import uuid
from zipfile import ZipFile, BadZipfile

from django.core.urlresolvers import reverse
from django.contrib import auth
from django.db import models
from django.dispatch import Signal

import autoslug
import tagging
from sorl import thumbnail

(STATUS_NEW, STATUS_LOCKED,
 STATUS_REJECTED, STATUS_INACTIVE,
 STATUS_ACTIVE) = xrange(5)

STATUSES = {
    STATUS_NEW: u"New",
    STATUS_LOCKED: u"Unreviewed and Locked",
    STATUS_REJECTED: u"Rejected",
    STATUS_INACTIVE: u"Invactive",
    STATUS_ACTIVE: u"Active",
}

VISIBLE_STATUSES = (STATUS_ACTIVE,)
EDITABLE_STATUSES = (STATUS_NEW, STATUS_ACTIVE)
REVIEWED_STATUSES = (STATUS_REJECTED, STATUS_INACTIVE, STATUS_ACTIVE)

class ExtensionManager(models.Manager):
    def visible(self):
        return self.filter(versions__status__in=VISIBLE_STATUSES).distinct()

class Extension(models.Model):
    name = models.CharField(max_length=200)
    uuid = models.CharField(max_length=200, unique=True, db_index=True)
    slug = autoslug.AutoSlugField(populate_from="name")
    creator = models.ForeignKey(auth.models.User, db_index=True)
    description = models.TextField()
    url = models.URLField(verify_exists=False)
    created = models.DateTimeField(auto_now_add=True)

    def make_screenshot_filename(self, filename):
        return os.path.join(self.uuid, filename)

    screenshot = thumbnail.ImageField(upload_to=make_screenshot_filename, blank=True)

    objects = ExtensionManager()

    def __unicode__(self):
        return self.uuid

    @property
    def visible_versions(self):
        return self.versions.filter(status__in=VISIBLE_STATUSES)

    @property
    def latest_version(self):
        qs = self.visible_versions.order_by("-version")
        if qs.exists():
            return qs[0]
        return None

    def user_has_access(self, user):
        if user == self.creator:
            return True
        if user.has_perm('extensions.can-modify-data'):
            return True
        return False

tagging.register(Extension)

class InvalidExtensionData(Exception):
    pass

class ExtensionVersion(models.Model):
    extension = models.ForeignKey(Extension, related_name="versions")
    version = models.IntegerField(default=0)
    extra_json_fields = models.TextField()
    status = models.PositiveIntegerField(choices=STATUSES.items())

    class Meta:
        unique_together = ('extension', 'version'),

    def __unicode__(self):
        return "Version %d of %s" % (self.version, self.extension)

    def make_filename(self, filename):
        return os.path.join(self.extension.uuid, str(self.version),
                            self.extension.slug + ".shell-extension.zip")

    source = models.FileField(upload_to=make_filename)

    def get_manifest_url(self, request):
        path = reverse('extensions-manifest',
                       kwargs=dict(uuid=self.extension.uuid, ver=self.pk))
        return request.build_absolute_uri(path)

    def make_metadata_json(self):
        """
        Return generated contents of metadata.json
        """
        data = json.loads(self.extra_json_fields)
        fields = dict(
            _generated  = "Generated by SweetTooth, do not edit",
            name        = self.extension.name,
            description = self.extension.description,
            url         = self.extension.url,
            uuid        = self.extension.uuid,
        )

        data.update(fields)
        return data

    def get_zipfile(self, mode):
        return ZipFile(self.source.storage.path(self.source.name), mode)

    def replace_metadata_json(self):
        """
        In the uploaded extension zipfile, edit metadata.json
        to reflect the new contents.
        """
        zipfile = self.get_zipfile("a")
        metadata = self.make_metadata_json()
        zipfile.writestr("metadata.json", json.dumps(metadata, sort_keys=True, indent=2))
        zipfile.close()

    def parse_metadata_json(self, metadata):
        """
        Given the contents of a metadata.json file, fill in the fields
        of the version and associated extension.
        """
        assert self.extension is not None

        # Only parse the standard data for a new extension
        if self.extension.pk is None:
            self.extension.name = metadata.pop('name', "")
            self.extension.description = metadata.pop('description', "")
            self.extension.url = metadata.pop('url', "")
            self.extension.uuid = metadata.pop('uuid', str(uuid.uuid1()))
            self.extension.save()

            # Due to Django ORM magic and stupidity, this is unfortunately necessary
            self.extension = self.extension

        # FIXME: We shouldn't do this, but Django saving requires it.
        if self.status is None:
            self.status = STATUS_NEW

        self.extra_json_fields = json.dumps(metadata)

        # get version number
        ver_ids = self.extension.versions.order_by('-version')
        try:
            ver_id = ver_ids[0].version + 1
        except IndexError:
            # New extension, no versions yet
            ver_id = 1

        self.version = ver_id

        # ManyToManyField requires a PK, so we need to save.
        self.save()

        for sv_string in metadata.pop('shell-version', []):
            sv = ShellVersion.objects.get_for_version_string(sv_string)
            self.shell_versions.add(sv)

        self.save()

    def parse_zipfile(self, uploaded_file):
        """
        Given a file, create an extension and version, populated
        with the data from the metadata.json and return them.
        """
        try:
            zipfile = ZipFile(uploaded_file, 'r')
        except BadZipfile:
            raise InvalidExtensionData("Invalid zip file")

        try:
            metadata = json.load(zipfile.open('metadata.json', 'r'))
        except KeyError:
            # no metadata.json in archive, use web editor
            metadata = {}
        except ValueError:
            # invalid JSON file, raise error
            raise InvalidExtensionData("Invalid JSON data")

        self.parse_metadata_json(metadata)
        zipfile.close()

submitted_for_review = Signal(providing_args=["version"])
reviewed = Signal(providing_args=["version", "review"])
