# Upload an image

## When to use

Uploading an image from your server: a local file path, an open file object, raw bytes, or
a remote URL that Cloudinary fetches for you.

For uploads started in a browser, see [Sign a browser upload](sign-browser-upload.md).
For files over ~100 MB or long videos, see [Upload a large video](upload-large-video.md).
In a Django project, a model field can do this for you — see
[Use with Django](use-with-django.md).

## Complete flow

```python
import cloudinary
import cloudinary.uploader  # cloudinary.uploader must be imported explicitly

# Configuration is read from CLOUDINARY_URL automatically.


def main():
    result = cloudinary.uploader.upload(
        "https://res.cloudinary.com/demo/image/upload/sample.jpg",
        public_id="products/leather-bag",  # stable, addressable ID; omit for a random one
        tags=["catalog", "autumn"],
        context={"alt": "Brown leather shoulder bag"},
    )

    print(result["public_id"])   # 'products/leather-bag'
    print(result["asset_id"])    # 'f2a0b57ccc814b13ec05b897b1d41d83'
    print(result["secure_url"])  # canonical delivery URL of the original
    print(result["width"], result["height"], result["format"])  # 864 576 jpg
    return result


if __name__ == "__main__":
    try:
        main()
    except cloudinary.exceptions.Error as error:
        print("Upload failed: {0}".format(error))
        print("Check that CLOUDINARY_URL is set (Console > Settings > API Keys).")
        raise SystemExit(1)
```

A local path works the same way: `cloudinary.uploader.upload("photo.jpg")`. So does an
open file object, which is what you pass when handling a web request:
`cloudinary.uploader.upload(request.files["photo"])`.

Uploading to the same `public_id` again **replaces** the asset and keeps its
`asset_id`. Add `invalidate=True` to purge the old file from the CDN, or pass
`overwrite=False` to make a repeat upload return the existing asset untouched.

## Result fields to keep

Store `asset_id`. It never changes; `public_id` changes when an asset is renamed or
moved.

```python
record = {"asset_id": result["asset_id"], "public_id": result["public_id"]}
```

Look an asset up later with `cloudinary.api.resource_by_asset_id(asset_id)`, or
`cloudinary.api.resource(public_id)` while the ID is still current.

Also worth keeping: `version` (for cache-busting URLs), `format`, `width`, `height`, and
`bytes`. `secure_url` can always be rebuilt from the `public_id`, so storing it is
optional.

## Useful options

- `folder="products"` — upload into a folder, keeping the generated ID.
- `use_filename=True, unique_filename=False` — derive the `public_id` from the original
  filename instead of a random string.
- `eager=[{"width": 400, "height": 400, "crop": "fill"}]` — generate derived versions at
  upload time instead of on first request.
- `resource_type="auto"` — let Cloudinary decide between image, video, and raw.
- `notification_url="https://example.com/hook"` — get a webhook when processing finishes.

## Size limits

Two separate limits apply, and they fail the same way with
`File size too large. Got NNN. Maximum is NNN.`:

- **100 MB per request.** A single `upload` call cannot exceed this, whatever your plan.
  Above it, use [`upload_large`](upload-large-video.md) — it splits the file into chunks
  (20 MB by default, set with `chunk_size`) and uploads them sequentially.
- **Your product environment's maximum asset size**, which varies by plan and is
  unrelated to the per-request ceiling. `upload_large` does not raise it.

Read the real values for your environment rather than assuming:

```python
media_limits = cloudinary.api.usage()["media_limits"]
print(media_limits["image_max_size_bytes"])
print(media_limits["video_max_size_bytes"])
print(media_limits["image_max_px"], media_limits["asset_max_total_px"])
```

If an asset exceeds the environment maximum, chunking will not help — compress or resize
it before uploading, or upgrade the plan.

## Troubleshooting

- `Must supply api_key` — the SDK is not configured. See
  [Configure Cloudinary](configure-cloudinary.md).
- `Invalid Signature` — a wrong `api_secret` for this cloud name.
- `File size too large` — see [Size limits](#size-limits); either the request exceeded
  the 100 MB single-request ceiling, or the asset exceeds your product environment's
  maximum.
- `Invalid image file` — the file is not a format Cloudinary can decode.
- `Resource not found - <url>` when fetching a remote URL — the URL is not publicly
  reachable. Upload the bytes directly instead.
- `Resource not found - Error in loading <url> - HTML response` — the URL returned a web
  page (a login or error page) rather than an image.
- The upload succeeds but the delivery URL returns 403 with `x-cld-error: ACL deny` — you
  are on an unclaimed Claimable Cloud and delivering from a non-allow-listed address. See
  [Get Cloudinary credentials](get-credentials.md).

## Related

- Runnable example: `examples/upload-image.py`
- [Transform and deliver an image](transform-and-deliver-image.md) — what to do with the
  uploaded asset.
- [Sign a browser upload](sign-browser-upload.md) — uploads that start in the client.
- [Use with Django](use-with-django.md) — uploading through a model field.
- [Upload API reference](https://cloudinary.com/documentation/image_upload_api_reference.md)
