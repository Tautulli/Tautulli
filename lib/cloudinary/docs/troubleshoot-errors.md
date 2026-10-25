# Troubleshoot errors

## How this SDK reports errors

Failures raise exceptions from `cloudinary.exceptions`, mapped from the HTTP status:

| Exception | Status | Usual cause |
|---|---|---|
| `BadRequest` | 400 | Invalid parameter or value |
| `AuthorizationRequired` | 401 | Missing or wrong credentials, bad signature |
| `NotAllowed` | 403 | Valid credentials without permission for this operation |
| `NotFound` | 404 | No such asset, folder, or preset |
| `AlreadyExists` | 409 | The resource exists (duplicate `external_id`, folder) |
| `RateLimited` | 420 / 429 | Hourly API limit reached, **or** an add-on you are not subscribed to |
| `GeneralError` | 500 / 503 | A server-side failure |

All of them subclass `cloudinary.exceptions.Error`, so one handler catches everything:

```python
import cloudinary.exceptions

try:
    result = cloudinary.uploader.upload("photo.jpg")
except cloudinary.exceptions.NotFound:
    ...                                          # handle the specific case
except cloudinary.exceptions.Error as error:
    print("Cloudinary call failed: {0}".format(error))
```

Two things worth knowing:

- **Configuration problems raise `ValueError`, not a Cloudinary error.** `Must supply
  api_key` and the malformed-URL messages come from the SDK before any request is made,
  so they are not caught by `except cloudinary.exceptions.Error`.
- **Delivery failures are not exceptions.** URL building is local and always succeeds; a
  broken image is an HTTP status on the CDN request. Check the `x-cld-error` response
  header for the reason.

## Errors by symptom

### `Must supply api_key` / `Must supply cloud_name` / `Must supply api_secret`

The SDK is not configured, or is partially configured. `api_secret` is needed only for
uploads, Admin API calls, and signing — URL building needs just the cloud name.

Individual `CLOUDINARY_*` variables override `CLOUDINARY_URL` entirely: if
`CLOUDINARY_CLOUD_NAME` is set, `CLOUDINARY_URL` is ignored, which is a common way to end
up with a cloud name but no key. See [Configure Cloudinary](configure-cloudinary.md).

In Django, the `CLOUDINARY` settings dict is read *before* the environment, so a partial
dict masks a working `CLOUDINARY_URL`.

### `Invalid CLOUDINARY_URL scheme. Expecting to start with 'cloudinary://'`

The variable holds a bare cloud name, a full HTTPS URL, or an `account://` provisioning
URL. The format is `cloudinary://<api_key>:<api_secret>@<cloud_name>`.

### `Invalid Signature <hash>. String to sign - '<params>'`

The signature does not match the submitted parameters. The message prints exactly what
the server signed — compare it against what the client sent.

- For browser uploads: the signed and submitted parameters must match exactly, with
  nothing extra and nothing missing. See [Sign a browser upload](sign-browser-upload.md).
- For server-side calls: the `api_secret` does not belong to this cloud name. Re-copy all
  three values.

### `Resource not found`

- `Resource not found - <url>` while uploading — the remote URL is not publicly
  reachable.
- `Resource not found - Error in loading <url> - HTML response` — the URL returned a web
  page rather than a file.
- On `resource()`, `update()`, or `destroy()` — the `resource_type` or `type` is wrong.
  Both default to `image` / `upload`, so videos, raw files, and private assets need them
  stated explicitly.

### A delivery URL returns 404 but the asset exists

In order of likelihood:

1. Wrong `resource_type` — video URLs need `/video/upload/`. Use `CloudinaryVideo`, which
   sets it for you.
2. The asset was uploaded with `resource_type="raw"` — `upload_large` defaults to raw, so
   a video uploaded without `resource_type="video"` lands under `/raw/upload/` and no
   transformation works on it. See [Upload a large video](upload-large-video.md).
3. Moderation is pending — the asset is stored but not deliverable until approved. See
   [Moderate an upload](moderate-upload.md).
4. Wrong `type` — `private` and `authenticated` assets need that `type` and a signed URL.

### 403 with `x-cld-error: ACL deny`

An unclaimed Claimable Cloud delivers only to its allow-listed IPs. Uploads and Admin API
calls still work from anywhere, which is why this shows up as broken images beside
successful uploads. Deliver from an allowed address or claim the cloud — see
[Get Cloudinary credentials](get-credentials.md).

### `delivery_ips must contain at least one public IP address`

`create_cloud()` behind a VPN or corporate proxy: the request arrives from a private
address. Pass your public address explicitly. See
[Get Cloudinary credentials](get-credentials.md).

### `File size too large. Got <n>. Maximum is <n>.`

Two different limits produce this message. If the request exceeded the **100 MB
per-request ceiling**, use [`upload_large`](upload-large-video.md), which chunks it. If
the asset exceeds your **product environment's maximum asset size** (plan-dependent),
chunking will not help — compress, resize, or upgrade the plan. Read the real values from
`cloudinary.api.usage()["media_limits"]`; see [Size limits](upload-image.md#size-limits).

### `Rate limit exceeded` / `You don't have an active subscription for <add-on>`

Both raise `RateLimited`, but they are different problems:

- A genuine rate limit — the Admin API allows roughly 500 requests per hour on free
  plans. Batch operations, and prefer one Search call over many `resource()` calls. The
  response headers `x-featureratelimit-limit` and `-remaining` show the budget.
- An unsubscribed add-on — the message names the add-on. Enable it on the account;
  `moderation="manual"` needs no subscription.

### `423` while an asset is still processing

The asset is not yet available for the operation you requested — common right after
uploading a large video, or while an eager or add-on-driven transformation is still
running. This is transient: retry with backoff rather than treating it as a failure. For
long jobs, prefer `eager_async=True` with a `notification_url` over polling.

Note that 423 is not in this SDK's status-to-exception map, so it surfaces as a plain
`Exception` rather than a `cloudinary.exceptions.Error` subclass — a handler that catches
only `cloudinary.exceptions.Error` will miss it.

### A transformation is missing from the generated URL

The SDK drops parameters it does not recognize, silently. Check the spelling against the
[transformation reference](https://cloudinary.com/documentation/transformation_reference.md),
or pass it through verbatim with `raw_transformation="e_whatever:100"`.

### `Query Error (at position N)` from Search

An unsupported expression. Leading wildcards are rejected (`context.alt:*bag*` fails,
`context.alt:bag*` works). Field matches use `:`, tag equality uses `=`.

### A newly uploaded asset is missing from Search results

The search index is eventually consistent and lags uploads by a few seconds. Use
`cloudinary.api.resource()` when you need read-after-write.

### `AttributeError: module 'cloudinary' has no attribute 'uploader'`

`import cloudinary` does not load the submodules. Add `import cloudinary.uploader` or
`import cloudinary.api`. See [Import and call the SDK](import-and-call.md).

### The URL prints as `('https://...', {})`

`cloudinary.utils.cloudinary_url()` returns a `(url, remaining_options)` tuple. Unpack it:
`url, _ = cloudinary.utils.cloudinary_url(...)`.

### Requests hang or time out

Set a shorter timeout (`timeout=30`), and configure a proxy with `api_proxy` in config if
your network requires one. Chunked uploads are sequential, so a large file legitimately
takes a long time.

## Still stuck

- Platform status: https://status.cloudinary.com — check this first. A widespread
  incident explains failures that look like a bug in your code.
- Every error message the API can return, per endpoint:
  [Admin API reference](https://cloudinary.com/documentation/admin_api.md) and
  [Upload API reference](https://cloudinary.com/documentation/image_upload_api_reference.md).
- Cross-product diagnosis index:
  https://cloudinary.com/documentation/llms-troubleshooting.txt
- SDK bugs: [GitHub issues](https://github.com/cloudinary/pycloudinary/issues).
  Account and platform questions: [Cloudinary support](https://support.cloudinary.com).
