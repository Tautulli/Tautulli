# Sign a browser upload

## When to use

Letting a browser or mobile app upload directly to Cloudinary, authorized by your server.
The file never passes through your application, but your `api_secret` never leaves it
either.

Your server signs a set of upload parameters; the client posts the file plus that
signature to Cloudinary. For server-side uploads, see
[Upload an image](upload-image.md).

## Complete flow

The server endpoint that issues a signature:

```python
import time

import cloudinary
import cloudinary.utils  # available after `import cloudinary`

# Configuration is read from CLOUDINARY_URL automatically.


def signature_payload():
    config = cloudinary.config()

    # Every parameter signed here must be sent by the client, byte for byte.
    params_to_sign = {
        "timestamp": int(time.time()),
        "folder": "user-uploads",
    }

    signature = cloudinary.utils.api_sign_request(params_to_sign, config.api_secret)

    return {
        "signature": signature,          # 40-character hex (SHA-1)
        "api_key": config.api_key,        # public, safe to send
        "cloud_name": config.cloud_name,
        **params_to_sign,
    }


if __name__ == "__main__":
    print(signature_payload())
```

The client posts to
`https://api.cloudinary.com/v1_1/<cloud_name>/image/upload` with the same parameters plus
`file`, `api_key`, and `signature`. Build that endpoint without hardcoding it:

```python
endpoint = cloudinary.utils.cloudinary_api_url("upload", resource_type="image")
# https://api.cloudinary.com/v1_1/<cloud>/image/upload
```

## The rule that causes most failures

**The signed parameters and the submitted parameters must match exactly.** If the client
adds `tags` that the server did not sign, or the server signs a `folder` the client omits,
Cloudinary returns `Invalid Signature`. Sign every parameter the client will send, and
send nothing extra.

Signatures are timestamp-bound and valid for one hour. Issue one per upload rather than
caching.

## Restricting what the client may do

Signing authorizes an upload; it does not constrain it. To limit format, size, or
destination, sign a preset instead of raw parameters:

```python
params_to_sign = {"timestamp": int(time.time()), "upload_preset": "user-avatars"}
```

Create the preset once with the folder, `allowed_formats`, and transformations you want:

```python
import cloudinary.api

cloudinary.api.create_upload_preset(
    name="user-avatars",
    unsigned=False,
    folder="avatars",
    allowed_formats="jpg,png,webp",
    transformation=[{"width": 512, "height": 512, "crop": "fill", "gravity": "face"}],
)
```

## Unsigned uploads

An unsigned preset removes the server round trip entirely — and with it your control over
who uploads. Use it only for genuinely public uploads, with a deliberately restricted
preset (`unsigned=True`, fixed folder, `allowed_formats`, size caps):

```python
cloudinary.uploader.unsigned_upload("photo.jpg", "public-drop-box")
```

## Verifying the result

Cloudinary can sign its response and its webhooks so your server can trust them:

```python
cloudinary.utils.verify_api_response_signature(
    result["public_id"], result["version"], result["signature"]
)
```

For webhook payloads use
`cloudinary.utils.verify_notification_signature(body, timestamp, signature)`.

## Troubleshooting

- `Invalid Signature <hash>. String to sign - '<params>'` — the signed and submitted
  parameters differ. The error prints the exact string the server signed; compare it with
  what the client sent. This is almost always an extra or missing parameter, not a wrong
  secret.
- `Must supply api_secret` — the signing process has no credentials configured.
- `Stale request` — the `timestamp` is more than an hour old, or the server clock is
  wrong.
- `Upload preset not found` — the preset name does not exist on this cloud, or it is
  unsigned while you signed the request.
- The client gets a CORS error — you are posting to the wrong host. Uploads go to
  `api.cloudinary.com`, not `res.cloudinary.com`.

## Related

- Runnable example: `examples/sign-browser-upload.py`
- [Upload an image](upload-image.md) — server-side uploads.
- [Use with Django](use-with-django.md) — `CloudinaryJsFileField` renders a signed
  direct-upload widget for you.
- [Upload Widget](https://cloudinary.com/documentation/upload_widget.md) — a complete
  in-browser upload UI that consumes this signature.
- [Signature generation reference](https://cloudinary.com/documentation/signatures.md)
