# Transform and deliver an image

## When to use

Building a delivery URL for an image already in Cloudinary: resized, cropped, format-
and quality-optimized, or generatively edited.

URL generation is **local**. No network call, no `api_secret` — only the cloud name is
required. The derived image is created by Cloudinary on first request and then served
from CDN cache.

For video, see [Transform and deliver a video](transform-and-deliver-video.md). For
rendering URLs in Django templates, see [Use with Django](use-with-django.md).

## Optimized image URL

```python
import cloudinary  # configuration is read from CLOUDINARY_URL

image = cloudinary.CloudinaryImage("products/leather-bag")

url = image.build_url(
    width=400,
    height=400,
    crop="fill",          # fill the box, cropping the overflow
    gravity="auto",       # let Cloudinary choose the crop centre
    fetch_format="auto",  # WebP or AVIF when the browser supports it
    quality="auto",       # per-image quality tuning
    secure=True,
)
print(url)
# https://res.cloudinary.com/<cloud>/image/upload/c_fill,f_auto,g_auto,h_400,q_auto,w_400/v1/products/leather-bag
```

`fetch_format="auto"` and `quality="auto"` are the two options worth setting on almost
every image: together they typically cut bytes by half with no visible change.

Parameters are emitted in alphabetical order, not the order you pass them — the URL above
is stable and cache-friendly regardless of keyword order.

The `/v1/` segment appears when the `public_id` contains a slash and no version is known.
It is a placeholder that delivers correctly. Pass the `version` from the upload result to
get a cache-busting URL, or `force_version=False` to leave it out for a top-level
`public_id`.

## The functional alternative

`cloudinary.utils.cloudinary_url` does the same job without an object. It returns a
**tuple** of `(url, remaining_options)`, so unpack it:

```python
import cloudinary.utils

url, _ = cloudinary.utils.cloudinary_url(
    "products/leather-bag", width=400, crop="scale", fetch_format="auto", quality="auto", secure=True
)
```

Ignoring the second element and using the tuple as a URL is the most common mistake here.

## An `<img>` tag instead of a URL

```python
tag = cloudinary.CloudinaryImage("products/leather-bag").image(
    width=300, crop="scale", fetch_format="auto", quality="auto", secure=True, alt="Leather bag"
)
# <img alt="Leather bag" src="https://res.cloudinary.com/<cloud>/image/upload/c_scale,f_auto,q_auto,w_300/v1/products/leather-bag" width="300"/>
```

Transformation options that affect the URL are consumed; presentation attributes such as
`alt` are rendered onto the tag. For responsive markup, pass `srcset={"breakpoints": [...]}`
or use `.picture(sources=[...])`.

## Chained transformations

Pass a list to `transformation=` when one step must complete before the next — cropping
first, then applying an effect:

```python
url = cloudinary.CloudinaryImage("products/leather-bag").build_url(
    transformation=[
        {"width": 600, "height": 600, "crop": "fill", "gravity": "auto"},
        {"effect": "sharpen"},
    ],
    fetch_format="auto",
    quality="auto",
    secure=True,
)
# .../c_fill,g_auto,h_600,w_600/e_sharpen/f_auto,q_auto/v1/products/leather-bag
```

## Generative and AI edits

These are **generic strings, not typed builders**. Pass the effect name exactly as the
transformation reference spells it:

```python
image = cloudinary.CloudinaryImage("products/leather-bag")

image.build_url(effect="gen_restore", secure=True)                    # e_gen_restore
image.build_url(effect="gen_remove:prompt_hat", secure=True)          # e_gen_remove:prompt_hat
image.build_url(effect="background_removal", secure=True)             # e_background_removal
image.build_url(background="gen_fill", width=1200, height=630,
                crop="pad", secure=True)                              # b_gen_fill,c_pad,...
```

Anything the SDK does not model can be passed verbatim with
`raw_transformation="e_vectorize:colors:8"`. Generative add-ons are billed and some
require enabling on your account; the first request is slow while the derived asset is
produced.

## Delivering a private or authenticated asset

```python
url = cloudinary.CloudinaryImage("contracts/invoice").build_url(
    type="authenticated", sign_url=True, secure=True
)
# .../image/authenticated/s--<signature>--/v1/contracts/invoice
```

Signing needs the `api_secret`, so it belongs on your server.

## Troubleshooting

- The URL 404s — the `public_id` is wrong, or the asset is a different `resource_type`
  (`video`, `raw`) or `type` (`private`, `authenticated`). Confirm with
  `cloudinary.api.resource(public_id)`.
- `x-cld-error: ACL deny` — an unclaimed Claimable Cloud delivering to a
  non-allow-listed address. See [Get Cloudinary credentials](get-credentials.md).
- The URL contains a literal `('https://...', {})` — you used `cloudinary_url` without
  unpacking the tuple.
- A transformation silently disappears from the URL — the parameter is not one the SDK
  recognizes. Check the spelling against the
  [transformation reference](https://cloudinary.com/documentation/transformation_reference.md),
  or use `raw_transformation`.
- `Invalid transformation component` on first request — the effect name or its argument
  is not valid; Cloudinary reports this at delivery time, not when building the URL.
- The image is stale after re-uploading to the same `public_id` — CDN cache. Upload with
  `invalidate=True`, or include `version=result["version"]` in the URL.

## Related

- Runnable example: `examples/transform-and-deliver-image.py`
- [Transform and deliver a video](transform-and-deliver-video.md)
- [Upload an image](upload-image.md)
- [Transformation reference](https://cloudinary.com/documentation/transformation_reference.md)
  — every parameter and its accepted values.
- [Image optimization](https://cloudinary.com/documentation/image_optimization.md)
