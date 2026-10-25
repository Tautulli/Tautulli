# Configure Cloudinary

## When to use

Do this once per process before any upload, admin, or URL-generation call.

**Prerequisite:** a `cloud_name`, `api_key`, and `api_secret`. If you do not have them,
see [Get Cloudinary credentials](get-credentials.md) —
`cloudinary.provisioning.create_cloud()` provisions a working cloud with delayed email verification so you can immediately get up and running.

## Recommended: environment variable

Set `CLOUDINARY_URL` (from Console > Settings > API Keys, or from the
`api_environment_variable` field returned when you provision a cloud):

```bash
export CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>
```

```python
import cloudinary

# Configuration is read from CLOUDINARY_URL automatically on first use.
print(cloudinary.config().cloud_name)
```

## Alternative: explicit configuration

```python
import os
import cloudinary

cloudinary.config(
    cloud_name="my-cloud",
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True,
)
```

## Behavior you should know

- Configuration is **process-global**: `cloudinary.config()` affects every caller in the
  process. Pass per-call options as keyword arguments when you need to override one
  value for a single call.
- **Individual `CLOUDINARY_*` variables win over `CLOUDINARY_URL`.** If
  `CLOUDINARY_CLOUD_NAME` is set, the SDK reads every `CLOUDINARY_*` variable
  (`CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `CLOUDINARY_SECURE`, ...) and ignores
  `CLOUDINARY_URL` entirely. Use one style or the other, not both.
- Unset configuration keys read back as `None` instead of raising, so
  `cloudinary.config().api_secret` is a safe way to check whether credentials are
  present.
- `secure=True` produces `https://` delivery URLs. Set it in config once rather than
  per call.
- In Django, the `CLOUDINARY` dict in your settings module is read first, before the
  environment. See [Use with Django](use-with-django.md).
- Account-level (provisioning) operations use `CLOUDINARY_ACCOUNT_URL`
  (`account://<key>:<secret>@<account_id>`) instead.

## Validate configuration early

```python
import cloudinary

config = cloudinary.config()
if not (config.cloud_name and config.api_key and config.api_secret):
    raise RuntimeError("Cloudinary is not configured: set CLOUDINARY_URL.")
```

## Troubleshooting

- `Must supply cloud_name` / `Must supply api_key` — `CLOUDINARY_URL` is missing or
  malformed. It must start with `cloudinary://`.
- `ValueError: Invalid CLOUDINARY_URL scheme. Expecting to start with 'cloudinary://'` —
  the variable holds something else, often a bare cloud name or an `account://` URL.
- `Invalid Signature` on uploads — a wrong `api_secret`. Uploads report it this way
  instead of naming the secret; re-copy all three values from the console.
- `Must supply api_secret` when signing — you configured only a cloud name, which is
  enough for URL building but not for uploads or Admin API calls.

## Related

- [Get Cloudinary credentials](get-credentials.md) — if you do not have an account yet.
- [Import and call the SDK](import-and-call.md)
- [Sign a browser upload](sign-browser-upload.md) — keeping the secret server-side.
- [Python and Django SDK guide](https://cloudinary.com/documentation/django_integration.md)
