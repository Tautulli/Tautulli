# Use with Django

## When to use

Integrating Cloudinary into a Django project: a model field that uploads on save, form
fields that accept uploads, and template tags that render delivery URLs.

Everything in the other pages works unchanged inside Django — this page covers only the
Django-specific surface. For Flask, FastAPI, or any other framework, use the pure-Python
pages directly; there is no framework-specific layer to learn.

## Setup

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "cloudinary",
]

# Credentials: either set CLOUDINARY_URL in the environment (recommended),
# or configure them here. This dict is read before the environment.
CLOUDINARY = {
    "cloud_name": "my-cloud",
    "api_key": "123456789012345",
    "api_secret": os.environ["CLOUDINARY_API_SECRET"],
    "secure": True,
}
```

Adding `"cloudinary"` to `INSTALLED_APPS` is what makes the template tags and bundled
static files available. It is not needed for `cloudinary.uploader` or the Admin API.

## A model field that uploads on save

```python
# models.py
from django.db import models
from cloudinary.models import CloudinaryField


class Product(models.Model):
    name = models.CharField(max_length=100)
    image = CloudinaryField(
        "image",
        folder="products",          # any upload option is accepted here
        width_field="image_width",
        height_field="image_height",
    )
    image_width = models.IntegerField(null=True, blank=True)
    image_height = models.IntegerField(null=True, blank=True)
```

Assigning an uploaded file and saving performs the upload:

```python
product = Product(name="Leather bag", image=request.FILES["image"])
product.save()

product.image.public_id                      # 'products/abc123'
product.image.build_url(width=400, crop="fill", secure=True)
product.image.url                            # the plain delivery URL
```

The column is a `varchar(255)` storing
`[resource_type/type/][v<version>/]public_id[.format]`, so switching to `CloudinaryField`
from an `ImageField` needs a data migration, not just a schema one.

Reading the field gives you a `CloudinaryResource`, which has the same `build_url()` and
`image()` methods as `CloudinaryImage` — see
[Transform and deliver an image](transform-and-deliver-image.md).

Upload options passed to `CloudinaryField` must be real upload parameters (they are
filtered against the SDK's whitelist); unknown keys are dropped silently. A callable is
accepted for values that depend on the instance.

## Forms

Three form fields, for three upload paths:

```python
# forms.py
from django import forms
from cloudinary.forms import CloudinaryFileField, CloudinaryJsFileField, CloudinaryUnsignedJsFileField


class ServerSideForm(forms.Form):
    # The file reaches your server, which uploads it.
    photo = CloudinaryFileField(options={"folder": "uploads", "tags": ["web"]})


class DirectUploadForm(forms.Form):
    # The browser uploads straight to Cloudinary with a server-generated signature.
    photo = CloudinaryJsFileField(options={"folder": "uploads"})


class UnsignedUploadForm(forms.Form):
    # No signature; constrained by the preset instead.
    photo = CloudinaryUnsignedJsFileField("my-preset", options={"folder": "uploads"})
```

`CloudinaryJsFileField` renders the widget and signs the request for you — the mechanism
described in [Sign a browser upload](sign-browser-upload.md). It needs the bundled
JavaScript and a callback hook in the view:

```python
# views.py
from cloudinary.forms import cl_init_js_callbacks


def upload_view(request):
    form = DirectUploadForm(request.POST or None)
    if request.method == "GET":
        cl_init_js_callbacks(form, request)
    elif form.is_valid():
        form.save()  # or read form.cleaned_data["photo"]
    return render(request, "upload.html", {"form": form})
```

## Templates

```django
{% load cloudinary %}

{# Include the JS needed by the direct-upload widget #}
{% cloudinary_includes %}
{% cloudinary_js_config %}

{# An <img> tag from a public ID or a model field #}
{% cloudinary "products/leather-bag" width=400 height=400 crop="fill" fetch_format="auto" quality="auto" %}
{% cloudinary product.image width=400 crop="fill" %}

{# Just the URL, for use in an attribute #}
<img src="{% cloudinary_url product.image width=200 crop="thumb" gravity="face" %}">
```

`{% cloudinary_url %}` sets `secure=True` automatically when the request is HTTPS.

## Migrations

`CloudinaryField` serializes its upload options into the migration file. Changing an
option (a different `folder`, for instance) generates a new migration that alters nothing
in the database — harmless, but expected. Keep the generated migrations; do not hand-edit
them to remove the options.

## Not part of this package

- **A staticfiles storage backend.** This SDK has no storage class for serving Django's
  `static/` or `media/` through Cloudinary. Upload through `CloudinaryField` or
  `uploader.upload()` and deliver the resulting URLs.
- **A ready-made admin widget.** `CloudinaryField` works in the Django admin through its
  default form field; there is no custom admin media browser.

## Troubleshooting

- `Invalid template library specified` / `'cloudinary' is not a registered tag library` —
  `"cloudinary"` is missing from `INSTALLED_APPS`.
- The upload widget renders but nothing uploads — `{% cloudinary_includes %}` is missing,
  or `cl_init_js_callbacks(form, request)` was not called in the GET branch.
- `Must supply api_key` in a Django shell — the `CLOUDINARY` settings dict is incomplete
  and no `CLOUDINARY_URL` is set. The settings dict takes precedence, so a partial dict
  masks a working environment variable.
- The field stores a value but delivery 404s — the asset is a video or raw file; pass
  `resource_type="video"` to `CloudinaryField`.
- `Invalid Signature` from a direct-upload form — the client posted parameters the server
  did not sign. Keep the widget's `options` as the single source of truth.
- Tests that touch a `CloudinaryField` hit the network — the field uploads on save. Mock
  `cloudinary.uploader.upload_resource` in unit tests, as `django_tests/` does.

## Related

- [Upload an image](upload-image.md) — the underlying upload call.
- [Sign a browser upload](sign-browser-upload.md) — what `CloudinaryJsFileField` does.
- [Transform and deliver an image](transform-and-deliver-image.md) — `build_url()` options.
- [Configure Cloudinary](configure-cloudinary.md)
- [Django SDK guide](https://cloudinary.com/documentation/django_integration.md)
- Full sample project:
  [cloudinary-django-sample](https://github.com/cloudinary/cloudinary-django-sample)
