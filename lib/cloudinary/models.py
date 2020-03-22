import re

from cloudinary import CloudinaryResource, forms, uploader
from django.core.files.uploadedfile import UploadedFile
from django.db import models
from cloudinary.uploader import upload_options
from cloudinary.utils import upload_params

# Add introspection rules for South, if it's installed.
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^cloudinary.models.CloudinaryField"])
except ImportError:
    pass

CLOUDINARY_FIELD_DB_RE = r'(?:(?P<resource_type>image|raw|video)/' \
                         r'(?P<type>upload|private|authenticated)/)?' \
                         r'(?:v(?P<version>\d+)/)?' \
                         r'(?P<public_id>.*?)' \
                         r'(\.(?P<format>[^.]+))?$'


def with_metaclass(meta, *bases):
    """
    Create a base class with a metaclass.

    This requires a bit of explanation: the basic idea is to make a dummy
    metaclass for one level of class instantiation that replaces itself with
    the actual metaclass.

    Taken from six - https://pythonhosted.org/six/
    """
    class metaclass(meta):
        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)
    return type.__new__(metaclass, 'temporary_class', (), {})


class CloudinaryField(models.Field):
    description = "A resource stored in Cloudinary"

    def __init__(self, *args, **kwargs):
        self.default_form_class = kwargs.pop("default_form_class", forms.CloudinaryFileField)
        self.type = kwargs.pop("type", "upload")
        self.resource_type = kwargs.pop("resource_type", "image")
        self.width_field = kwargs.pop("width_field", None)
        self.height_field = kwargs.pop("height_field", None)
        # Collect all options related to Cloudinary upload
        self.options = {key: kwargs.pop(key) for key in set(kwargs.keys()) if key in upload_params + upload_options}

        field_options = kwargs
        field_options['max_length'] = 255
        super(CloudinaryField, self).__init__(*args, **field_options)

    def get_internal_type(self):
        return 'CharField'

    def value_to_string(self, obj):
        """
        We need to support both legacy `_get_val_from_obj` and new `value_from_object` models.Field methods.
        It would be better to wrap it with try -> except AttributeError -> fallback to legacy.
        Unfortunately, we can catch AttributeError exception from `value_from_object` function itself.
        Parsing exception string is an overkill here, that's why we check for attribute existence

        :param obj: Value to serialize

        :return: Serialized value
        """

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

    def from_db_value(self, value, expression, connection, *args, **kwargs):
        # TODO: when dropping support for versions prior to 2.0, you may return
        #   the signature to from_db_value(value, expression, connection)
        if value is not None:
            return self.parse_cloudinary_resource(value)

    def to_python(self, value):
        if isinstance(value, CloudinaryResource):
            return value
        elif isinstance(value, UploadedFile):
            return value
        elif value is None or value is False:
            return value
        else:
            return self.parse_cloudinary_resource(value)

    def pre_save(self, model_instance, add):
        value = super(CloudinaryField, self).pre_save(model_instance, add)
        if isinstance(value, UploadedFile):
            options = {"type": self.type, "resource_type": self.resource_type}
            options.update(self.options)
            instance_value = uploader.upload_resource(value, **options)
            setattr(model_instance, self.attname, instance_value)
            if self.width_field:
                setattr(model_instance, self.width_field, instance_value.metadata.get('width'))
            if self.height_field:
                setattr(model_instance, self.height_field, instance_value.metadata.get('height'))
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
