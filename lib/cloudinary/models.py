import re


from cloudinary import CloudinaryResource, forms, uploader

from django.core.files.uploadedfile import UploadedFile
from django.db import models

# Add introspection rules for South, if it's installed.
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^cloudinary.models.CloudinaryField"])
except ImportError:
    pass

CLOUDINARY_FIELD_DB_RE = r'(?:(?P<resource_type>image|raw|video)/(?P<type>upload|private|authenticated)/)?(?:v(?P<version>\d+)/)?(?P<public_id>.*?)(\.(?P<format>[^.]+))?$'


# Taken from six - https://pythonhosted.org/six/
def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})


class CloudinaryField(models.Field):
    description = "A resource stored in Cloudinary"

    def __init__(self, *args, **kwargs):
        options = {'max_length': 255}
        self.default_form_class = kwargs.pop("default_form_class", forms.CloudinaryFileField)
        options.update(kwargs)
        self.type = options.pop("type", "upload")
        self.resource_type = options.pop("resource_type", "image")
        self.width_field = options.pop("width_field", None)
        self.height_field = options.pop("height_field", None)
        super(CloudinaryField, self).__init__(*args, **options)

    def get_internal_type(self):
        return 'CharField'

    def value_to_string(self, obj):
        # We need to support both legacy `_get_val_from_obj` and new `value_from_object` models.Field methods.
        # It would be better to wrap it with try -> except AttributeError -> fallback to legacy.
        # Unfortunately, we can catch AttributeError exception from `value_from_object` function itself.
        # Parsing exception string is an overkill here, that's why we check for attribute existence

        if hasattr(self, 'value_from_object'):
            value = self.value_from_object(obj)
        else:  # fallback for legacy django versions
            value = self._get_val_from_obj(obj)

        return self.get_prep_value(value)

    def parse_cloudinary_resource(self, value):
        m = re.match(CLOUDINARY_FIELD_DB_RE, value)
        resource_type = m.group('resource_type') or self.resource_type
        upload_type = m.group('type') or self.type
        return CloudinaryResource(
            type=upload_type,
            resource_type=resource_type,
            version=m.group('version'),
            public_id=m.group('public_id'),
            format=m.group('format')
        )

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return self.parse_cloudinary_resource(value)

    def to_python(self, value):
        if isinstance(value, CloudinaryResource):
            return value
        elif isinstance(value, UploadedFile):
            return value
        elif value is None:
            return value
        else:
            return self.parse_cloudinary_resource(value)

    def upload_options_with_filename(self, model_instance, filename):
        return self.upload_options(model_instance)

    def upload_options(self, model_instance):
        return {}

    def pre_save(self, model_instance, add):
        value = super(CloudinaryField, self).pre_save(model_instance, add)
        if isinstance(value, UploadedFile):
            options = {"type": self.type, "resource_type": self.resource_type}
            options.update(self.upload_options_with_filename(model_instance, value.name))
            instance_value = uploader.upload_resource(value, **options)
            setattr(model_instance, self.attname, instance_value)
            if self.width_field:
                setattr(model_instance, self.width_field, instance_value.metadata['width'])
            if self.height_field:
                setattr(model_instance, self.height_field, instance_value.metadata['height'])
            return self.get_prep_value(instance_value)
        else:
            return value

    def get_prep_value(self, value):
        if not value:
            return self.get_default()
        if isinstance(value, CloudinaryResource):
            return value.get_prep_value()
        else:
            return value

    def formfield(self, **kwargs):
        options = {"type": self.type, "resource_type": self.resource_type}
        options.update(kwargs.pop('options', {}))
        defaults = {'form_class': self.default_form_class, 'options': options, 'autosave': False}
        defaults.update(kwargs)
        return super(CloudinaryField, self).formfield(**defaults)
