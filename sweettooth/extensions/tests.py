
import json
import os.path

from django.test import TestCase
from django.contrib.auth.models import User
from extensions import models

testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')

def get_test_zipfile(testname):
    return open(os.path.join(testdata_dir, testname, testname + ".zip"), 'rb')

class UploadTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testing', 'a@a.aa', 'jjj')

    def test_simple_metadata(self):
        metadata = {"name": "Test Metadata",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension(creator=self.user)
        version = models.ExtensionVersion()
        version.extension = extension
        version.parse_metadata_json(metadata)

        self.assertEquals(extension.name, "Test Metadata")
        self.assertEquals(extension.description, "Simple test metadata")
        self.assertEquals(extension.url, "http://test-metadata.gnome.org")

    def test_simple_zipdata_data(self):
        extension = models.Extension(creator=self.user)
        version = models.ExtensionVersion()
        version.extension = extension
        version.parse_zipfile(get_test_zipfile('SimpleExtension'))

        self.assertEquals(extension.name, "Test Extension")
        self.assertEquals(extension.description, "Simple test metadata")
        self.assertEquals(extension.url, "http://test-metadata.gnome.org")

    def test_extra_metadata(self):
        extension = models.Extension(creator=self.user)
        version = models.ExtensionVersion()
        version.extension = extension
        version.parse_zipfile(get_test_zipfile('ExtraMetadata'))

        extra = json.loads(version.extra_json_fields)
        self.assertEquals(extra["extra"], "This is some good data")
        self.assertTrue("description" not in extra)
        self.assertTrue("url" not in extra)

class ExtensionVersionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testing', 'a@a.aa', 'jjj')

    def test_single_version(self):
        metadata = {"name": "Test Metadata",
                    "uuid": "test-1@gnome.org",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension(creator=self.user)
        version = models.ExtensionVersion()
        version.extension = extension
        version.parse_metadata_json(metadata)

        version.status = models.STATUS_ACTIVE
        version.save()

        self.assertEquals(version.version, 1)
        self.assertEquals(extension.latest_version, version)

    def test_multiple_versions(self):
        metadata = {"name": "Test Metadata 2",
                    "uuid": "test-2@gnome.org",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension(creator=self.user)

        v1 = models.ExtensionVersion()
        v1.extension = extension
        v1.status = models.STATUS_ACTIVE
        v1.parse_metadata_json(metadata)
        v1.save()
        self.assertEquals(v1.version, 1)

        v2 = models.ExtensionVersion()
        v2.extension = extension
        v2.status = models.STATUS_ACTIVE
        v2.parse_metadata_json(metadata)
        v2.save()
        self.assertEquals(v2.version, 2)

        self.assertEquals(list(extension.visible_versions.order_by('version')), [v1, v2])
        self.assertEquals(extension.latest_version, v2)

    def test_unpublished_version(self):
        metadata = {"name": "Test Metadata 3",
                    "uuid": "test-3@gnome.org",
                    "description": "Simple test metadata",
                    "url": "http://test-metadata.gnome.org"}

        extension = models.Extension(creator=self.user)

        v1 = models.ExtensionVersion()
        v1.extension = extension
        v1.parse_metadata_json(metadata)
        v1.status = models.STATUS_ACTIVE
        v1.save()
        self.assertEquals(v1.version, 1)

        v2 = models.ExtensionVersion()
        v2.extension = extension
        v2.status = models.STATUS_NEW
        v2.parse_metadata_json(metadata)
        v2.save()
        self.assertEquals(v2.version, 2)

        self.assertEquals(list(extension.visible_versions.order_by('version')), [v1])
        self.assertEquals(extension.latest_version, v1)

        v3 = models.ExtensionVersion()
        v3.extension = extension
        v3.status = models.STATUS_ACTIVE
        v3.parse_metadata_json(metadata)
        v3.save()
        self.assertEquals(v3.version, 3)

        self.assertEquals(list(extension.visible_versions.order_by('version')), [v1, v3])
        self.assertEquals(extension.latest_version, v3)
