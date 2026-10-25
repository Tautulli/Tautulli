# Import and call the SDK

```python
import cloudinary
import cloudinary.uploader
import cloudinary.api

cloudinary.uploader.upload("photo.jpg")
cloudinary.api.resource("photo")
cloudinary.CloudinaryImage("photo").build_url(width=400, crop="fill")
```

Import the submodules you use explicitly. `import cloudinary` on its own gives you
`config()`, `CloudinaryImage`, `CloudinaryVideo`, `Search`, and `cloudinary.utils`,
but **not** `cloudinary.uploader` or `cloudinary.api` — reaching for those raises
`AttributeError: module 'cloudinary' has no attribute 'uploader'` until you import
them.

Calls are synchronous and return plain dictionaries. Positional arguments come first,
then keyword options that pass through to the API:
`cloudinary.uploader.upload("photo.jpg", public_id="hero", folder="products")`.

Configuration is read from the `CLOUDINARY_URL` environment variable on first use, so
no setup call is needed. See [Configure Cloudinary](configure-cloudinary.md).

## Related

- [Configure Cloudinary](configure-cloudinary.md)
- [Python and Django SDK guide](https://cloudinary.com/documentation/django_integration.md)
