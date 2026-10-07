# Upload a large video

## When to use

Uploading a file too large for a single request — videos, long audio, big archives.
`upload_large` splits the file into chunks and reassembles them server-side.

Use it for anything over ~100 MB, and for any video where a plain `upload` has timed out.
Smaller files should use [Upload an image](upload-image.md); the plain `upload` function
handles video too.

## Complete flow

```python
import cloudinary
import cloudinary.uploader  # cloudinary.uploader must be imported explicitly

# Configuration is read from CLOUDINARY_URL automatically.


def main(path="product-tour.mp4"):
    result = cloudinary.uploader.upload_large(
        path,
        resource_type="video",         # required: the default is "raw"
        public_id="marketing/product-tour",
        chunk_size=20000000,           # 20 MB, the default
        eager=[{"streaming_profile": "hd", "format": "m3u8"}],
        eager_async=True,              # transcode in the background
        notification_url=None,         # set a webhook URL to learn when eager work finishes
    )

    print(result["public_id"])   # 'marketing/product-tour'
    print(result["asset_id"])
    print(result["duration"])   # 34.6 — seconds
    print(result["secure_url"])
    return result


if __name__ == "__main__":
    try:
        main()
    except cloudinary.exceptions.Error as error:
        print("Upload failed: {0}".format(error))
        print("Check that CLOUDINARY_URL is set (Console > Settings > API Keys).")
        raise SystemExit(1)
```

**Pass `resource_type="video"`.** `upload_large` defaults to `raw`, and a raw upload
*succeeds* — it stores the file as an opaque blob under a `public_id` with the extension
appended (`marketing/product-tour.mp4`), served from `/raw/upload/`. No error is raised,
but no video transformation, thumbnail, or streaming profile will ever work on it. If a
video is already stored that way, re-upload it with the right resource type and delete the
raw copy with
`cloudinary.uploader.destroy("<public_id>.mp4", resource_type="raw")`.

Chunks upload sequentially, so a large file takes as long as the sum of its parts. Each
chunk shares one `X-Unique-Upload-Id`, and only the final chunk returns the full asset
payload — the earlier calls return a short "parts uploaded" acknowledgement.

## Result fields to keep

Store `asset_id`. It never changes; `public_id` changes when an asset is renamed or
moved.

Video results also carry `duration`, `bit_rate`, `frame_rate`, `audio`, and `video`
sub-dictionaries with codec details — useful for deciding which renditions to generate.
`eager` entries appear in the result only when `eager_async=False`.

## Choosing a chunk size

`chunk_size` defaults to 20 MB and must be at least 5 MB. Smaller chunks retry faster on
a flaky connection; larger chunks mean fewer round trips. Keep the default unless uploads
are failing partway through.

## Uploading from a stream or a remote URL

A remote URL does not need chunking — Cloudinary fetches it directly, so plain `upload`
is the better choice:

```python
cloudinary.uploader.upload(
    "https://example.com/videos/product-tour.mp4", resource_type="video"
)
```

For a file object, pass it directly: `upload_large(open("video.mp4", "rb"),
resource_type="video")`.

## Troubleshooting

- `File size too large` from plain `upload` — this is the function to switch to.
- The upload succeeded but video transformations 404, and the URL contains `/raw/upload/`
  — `resource_type="video"` was omitted. See the note above.
- The upload restarts from the beginning after a network drop — chunks are not resumable
  across processes. Retry the whole call; partial uploads expire server-side.
- `Request Timeout` on a slow connection — raise the per-request timeout with
  `timeout=120`, or lower `chunk_size`.
- The video uploads but `.m3u8` 404s — the eager renditions are still transcoding
  (`eager_async=True`). Poll `cloudinary.api.resource(public_id)` or use
  `notification_url`.
- `File size too large` despite chunking — chunking only clears the 100 MB per-request
  ceiling, not your product environment's maximum asset size. Read the real values from
  `cloudinary.api.usage()["media_limits"]`; compress, resize, or upgrade the plan.

## Related

- Runnable example: `examples/upload-large-video.py` — downloads a sample video from the
  Cloudinary demo account, then uploads it in chunks.
- [Transform and deliver a video](transform-and-deliver-video.md) — delivery, players,
  and adaptive streaming.
- [Upload an image](upload-image.md) — the plain upload path.
- [Upload API reference](https://cloudinary.com/documentation/image_upload_api_reference.md)
