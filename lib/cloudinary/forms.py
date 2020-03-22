import json
import re

import cloudinary.uploader
import cloudinary.utils
from cloudinary import CloudinaryResource
from django import forms
from django.utils.translation import ugettext_lazy as _


def cl_init_js_callbacks(form, request):
    for field in form.fields.values():
        if isinstance(field, CloudinaryJsFileField):
            field.enable_callback(request)


class CloudinaryInput(forms.TextInput):
    input_type = 'file'

    def render(self, name, value, attrs=None, renderer=None):
        attrs = dict(self.attrs, **attrs)
        options = attrs.get('options', {})
        attrs["options"] = ''

        params = cloudinary.utils.build_upload_params(**options)
        if options.get("unsigned"):
            params = cloudinary.utils.cleanup_params(params)
        else:
            params = cloudinary.utils.sign_request(params, options)

        if 'resource_type' not in options:
            options['resource_type'] = 'auto'
        cloudinary_upload_url = cloudinary.utils.cloudinary_api_url("upload", **options)

        attrs["data-url"] = cloudinary_upload_url
        attrs["data-form-data"] = json.dumps(params)
        attrs["data-cloudinary-field"] = name
        chunk_size = options.get("chunk_size", None)
        if chunk_size:
            attrs["data-max-chunk-size"] = chunk_size
        attrs["class"] = " ".join(["cloudinary-fileupload", attrs.get("class", "")])

        widget = super(CloudinaryInput, self).render("file", None, attrs=attrs)
        if value:
            if isinstance(value, CloudinaryResource):
                value_string = value.get_presigned()
            else:
                value_string = value
            widget += forms.HiddenInput().render(name, value_string)
        return widget


class CloudinaryJsFileField(forms.Field):
    default_error_messages = {
        'required': _(u"No file selected!")
    }

    def __init__(self, attrs=None, options=None, autosave=True, *args, **kwargs):
        if attrs is None:
            attrs = {}
        if options is None:
            options = {}
        self.autosave = autosave
        attrs = attrs.copy()
        attrs["options"] = options.copy()

        field_options = {'widget': CloudinaryInput(attrs=attrs)}
        field_options.update(kwargs)
        super(CloudinaryJsFileField, self).__init__(*args, **field_options)

    def enable_callback(self, request):
        from django.contrib.staticfiles.storage import staticfiles_storage
        self.widget.attrs["options"]["callback"] = request.build_absolute_uri(
            staticfiles_storage.url("html/cloudinary_cors.html"))

    def to_python(self, value):
        """Convert to CloudinaryResource"""
        if not value:
            return None
        m = re.search(r'^([^/]+)/([^/]+)/v(\d+)/([^#]+)#([^/]+)$', value)
        if not m:
            raise forms.ValidationError("Invalid format")
        resource_type = m.group(1)
        upload_type = m.group(2)
        version = m.group(3)
        filename = m.group(4)
        signature = m.group(5)
        m = re.search(r'(.*)\.(.*)', filename)
        if not m:
            raise forms.ValidationError("Invalid file name")
        public_id = m.group(1)
        image_format = m.group(2)
        return CloudinaryResource(public_id,
                                  format=image_format,
                                  version=version,
                                  signature=signature,
                                  type=upload_type,
                                  resource_type=resource_type)

    def validate(self, value):
        """Validate the signature"""
        # Use the parent's handling of required fields, etc.
        super(CloudinaryJsFileField, self).validate(value)
        if not value:
            return
        if not value.validate():
            raise forms.ValidationError("Signature mismatch")


class CloudinaryUnsignedJsFileField(CloudinaryJsFileField):
    def __init__(self, upload_preset, attrs=None, options=None, autosave=True, *args, **kwargs):
        if attrs is None:
            attrs = {}
        if options is None:
            options = {}
        options = options.copy()
        options.update({"unsigned": True, "upload_preset": upload_preset})
        super(CloudinaryUnsignedJsFileField, self).__init__(
            attrs, options, autosave, *args, **kwargs)


class CloudinaryFileField(forms.FileField):
    my_default_error_messages = {
        'required': _(u"No file selected!")
    }
    default_error_messages = forms.FileField.default_error_messages.copy()
    default_error_messages.update(my_default_error_messages)

    def __init__(self, options=None, autosave=True, *args, **kwargs):
        self.autosave = autosave
        self.options = options or {}
        super(CloudinaryFileField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """Upload and convert to CloudinaryResource"""
        value = super(CloudinaryFileField, self).to_python(value)
        if not value:
            return None
        if self.autosave:
            return cloudinary.uploader.upload_image(value, **self.options)
        else:
            return value
