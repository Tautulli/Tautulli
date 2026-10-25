# Transform and deliver a video

## When to use

Building delivery URLs, player markup, poster frames, or adaptive streaming manifests for
a video already in Cloudinary.

Video needs `resource_type="video"` — that is the single most common source of 404s when
reusing image code. URL generation is local: no network call, no `api_secret`.

For images, see [Transform and deliver an image](transform-and-deliver-image.md). To get
a video in, see [Upload a large video](upload-large-video.md).

## Video URL only

`CloudinaryVideo` sets the resource type for you:

```python
import cloudinary  # configuration is read from CLOUDINARY_URL

video = cloudinary.CloudinaryVideo("marketing/product-tour")

url = video.build_url(
    width=1280,
    crop="scale",
    quality="auto",
    secure=True,
)
print(url)
# https://res.cloudinary.com/<cloud>/video/upload/c_scale,q_auto,w_1280/v1/marketing/product-tour
```

With `CloudinaryImage` or `cloudinary_url`, pass `resource_type="video"` yourself.

## Player markup

```python
tag = cloudinary.CloudinaryVideo("marketing/product-tour").video(
    width=640, controls=True, secure=True
)
```

This renders a `<video>` element with a generated `poster` attribute and one `<source>`
per format — `webm`, `mp4`, and `ogv` by default:

```html
<video controls poster="https://res.cloudinary.com/<cloud>/video/upload/w_640/v1/marketing/product-tour.jpg" width="640">
  <source src="https://res.cloudinary.com/<cloud>/video/upload/w_640/v1/marketing/product-tour.webm" type="video/webm">
  <source src="https://res.cloudinary.com/<cloud>/video/upload/w_640/v1/marketing/product-tour.mp4" type="video/mp4">
  <source src="https://res.cloudinary.com/<cloud>/video/upload/w_640/v1/marketing/product-tour.ogv" type="video/ogg">
</video>
```

Narrow the list with `source_types=["mp4", "webm"]`, or use `sources=` to pair each
format with its own codec and transformations.

## Poster frame

A poster is an **image** derived from the video. Any of these work:

```python
video = cloudinary.CloudinaryVideo("marketing/product-tour")

video.video_thumbnail(width=640, secure=True)                    # default frame, as a URL
video.video_thumbnail(width=640, start_offset="3.5", secure=True) # a specific second
video.video(width=640, poster={"start_offset": "3.5"}, secure=True)  # inside the tag
```

Note: the dictionary form of `poster` does not inherit `secure=True` — it emits an
`http://` poster URL while the `<source>` elements stay `https://`. Pass a
pre-built URL instead when that matters:
`video.video(width=640, poster=video.video_thumbnail(start_offset="3.5", secure=True))`.

## Adaptive streaming (HLS / DASH)

Request the manifest by format, using a streaming profile:

```python
video = cloudinary.CloudinaryVideo("marketing/product-tour")

hls = video.build_url(streaming_profile="hd", format="m3u8", secure=True)
# .../video/upload/sp_hd/v1/marketing/product-tour.m3u8

dash = video.build_url(streaming_profile="hd", format="mpd", secure=True)
```

Generate the renditions at upload time with `eager` and `eager_async=True`; otherwise the
first viewer waits for transcoding. List available profiles with
`cloudinary.api.list_streaming_profiles()`.

## Trimming and video-specific options

```python
video.build_url(
    start_offset="2.0", end_offset="8.0",  # a 6-second clip
    width=720, crop="scale",
    video_codec="auto",                    # vc_auto — best codec per browser
    audio_codec="aac",
    quality="auto",
    secure=True,
)
```

Also available: `duration`, `fps`, `bit_rate`, `keyframe_interval`, `video_sampling`
(for animated previews), and `effect="accelerate:100"` for speed changes.

## Troubleshooting

- The URL 404s — you built an `image` URL. Video needs `resource_type="video"`, which
  `CloudinaryVideo` sets for you.
- The poster URL 404s — poster frames are images derived from the video; request `.jpg`,
  not the video format.
- `.m3u8` returns 404 or an empty manifest — the streaming profile renditions have not
  been generated yet, or the profile name does not exist on this cloud.
- The first request is very slow — transcoding happens on demand. Use `eager` with
  `eager_async=True` at upload time.
- `x-cld-error: ACL deny` — an unclaimed Claimable Cloud delivering to a
  non-allow-listed address. See [Get Cloudinary credentials](get-credentials.md).
- Audio plays but there is no picture, or the reverse — a codec the browser cannot
  decode. Use `video_codec="auto"` and keep an `mp4` source in the list.

## Related

- Runnable example: `examples/transform-and-deliver-video.py`
- [Transform and deliver an image](transform-and-deliver-image.md)
- [Upload a large video](upload-large-video.md)
- [Video transformation reference](https://cloudinary.com/documentation/video_manipulation_and_delivery.md)
- [Adaptive bitrate streaming](https://cloudinary.com/documentation/adaptive_bitrate_streaming.md)
