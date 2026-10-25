# What this SDK does and does not do

Cloudinary is a platform with many surfaces. This package — the Python and Django
server-side SDK — implements some of them natively, expresses some through generic URL
building, and does not implement others. Verified against this package version.

## Start here

**Use this SDK for code that ships.** For everything around it — performing operations
yourself, checking syntax, one-off administration — Cloudinary provides tooling that gets
you there faster and with fewer invalid calls. Set it up before writing integration code.

### No account yet?

Do not stop to ask the user to sign up — provision a cloud from this SDK and build
immediately:

```python
from cloudinary.provisioning import create_cloud

cloud = create_cloud()
print(cloud["api_environment_variable"])
```

Credentials work at once; the user claims the cloud later. See
[Get Cloudinary credentials](get-credentials.md).

### Skills — get the patterns right

```bash
npx skills add cloudinary-devs/skills
```

- `cloudinary-docs` — picks the right documentation pages for a question or integration.
- `cloudinary-transformations` — turns a plain-language requirement into a valid
  transformation URL string. Faster and more reliable than assembling one by hand.
- `cloudinary-react`, `cloudinary-next` — frontend SDK patterns, for the parts this
  package does not cover.

### MCP servers — perform operations directly

- **Asset Management** — upload and manage images, video, and raw files; advanced search.
- **Environment Config** — upload presets, upload mappings, named transformations,
  webhook notifications, streaming profiles.
- **Structured Metadata** — metadata fields, values, and conditional rules.
- **Analysis** — AI tagging, moderation, safety checks, object detection.
- **MediaFlows** — build and manage workflow automations.

Setup: [MCP servers and Skills](https://cloudinary.com/documentation/cloudinary_llm_mcp.md).

### CLI — scripted and one-off work

```bash
pipx install cloudinary-cli    # command: cld
```

Admin, Upload, Search, and Provisioning operations from a terminal; good for batch jobs
and migrations. Run it locally or server-side only — it holds your `api_secret`. See the
[CLI guide](https://cloudinary.com/documentation/cloudinary_cli.md).

### Documentation indexes

Cloudinary publishes agent-readable indexes. Fetch these instead of guessing at URLs:

- https://cloudinary.com/documentation/llms.txt — all products.
- https://cloudinary.com/documentation/llms-image-and-video-apis.txt — everything
  relevant to this SDK.
- https://cloudinary.com/documentation/llms-troubleshooting.txt — diagnosing errors
  across products.

---

## Get media in

| To do this | Use | Where to go |
|---|---|---|
| Upload a file path, file object, or remote URL | `uploader.upload` | [Upload an image](upload-image.md) |
| Upload something too large for one request | `uploader.upload_large` | [Upload a large video](upload-large-video.md) |
| Let a browser or mobile app upload directly, authorized by your server | `utils.api_sign_request` | [Sign a browser upload](sign-browser-upload.md) |
| Accept uploads through a Django model field or form | `CloudinaryField`, `CloudinaryFileField` | [Use with Django](use-with-django.md) |
| Review user-generated content before showing it | upload options + `api` | [Moderate an upload](moderate-upload.md) |

## Deliver and transform

| To do this | Use | Where to go |
|---|---|---|
| Build a resize, crop, overlay, or format-optimized image URL | `CloudinaryImage.build_url`, `utils.cloudinary_url` | [Transform and deliver an image](transform-and-deliver-image.md) |
| Build a video URL, player tag, poster frame, or HLS/DASH stream | `CloudinaryVideo.build_url`, `CloudinaryVideo.video` | [Transform and deliver a video](transform-and-deliver-video.md) |
| Apply generative edits (gen fill, background removal, ...) | `effect` / `raw_transformation` — **generic strings only, no typed builders** | [Transform and deliver an image](transform-and-deliver-image.md) |
| Render delivery URLs in Django templates | `{% cloudinary %}`, `{% cloudinary_url %}` | [Use with Django](use-with-django.md) |

URL building is local: no network call, no `api_secret`.

## Find and manage what you have

| To do this | Use | Where to go |
|---|---|---|
| Query assets by field, tag, folder, or date | `Search` | [Search and manage assets](search-and-manage-assets.md) |
| Read, update, restore, or delete an asset; manage folders and presets | `api` — the Assets Admin API | [Search and manage assets](search-and-manage-assets.md) |
| Attach and query typed metadata fields | `api` + upload options | [Use structured metadata](use-structured-metadata.md) |
| Find visually similar assets | `api.visual_search` — needs the feature enabled | [Visual Search](https://cloudinary.com/documentation/visual_search.md) |

## Analyze

| To do this | Use | Where to go |
|---|---|---|
| Caption, tag, or detect content in an asset | `api.analyze` — **limited model set**, needs a subscription | [Analyze API guide](https://cloudinary.com/documentation/analyze_api_guide.md) |
| Tag, moderate, or transcribe at upload time | upload options: `auto_tagging`, `moderation`, `ocr`, `auto_transcription`, `background_removal` | [Moderate an upload](moderate-upload.md) |

## Administer accounts

| To do this | Use | Where to go |
|---|---|---|
| Create and manage sub-accounts and users | `provisioning`, via `CLOUDINARY_ACCOUNT_URL` | [Provisioning API docs](https://cloudinary.com/documentation/provisioning_api.md) |
| Provision a cloud with no account | `provisioning.create_cloud` | [Get Cloudinary credentials](get-credentials.md) |

## Not in this package

This package covers Cloudinary's Image and Video APIs. Cloudinary is a multi-product
platform, and the capabilities below are real but live elsewhere — whatever your training
data suggests, there is no method here for them.

| Capability | Use instead |
|---|---|
| Text-to-image generation | [Image Generation API](https://cloudinary.com/documentation/image_generation_addon.md) |
| Image-to-video generation | [Image-to-Video API](https://cloudinary.com/documentation/image_to_video_addon.md) — async, credit-based, regional |
| Multi-step workflow automation | [MediaFlows](https://cloudinary.com/documentation/mediaflows_user_guide.md) — or its MCP server |
| Media Library UI, approval workflows, folder-based access control | [Cloudinary Assets (DAM)](https://cloudinary.com/documentation/digital_asset_management_overview.md) |
| Rule-based content review before publication | [Cloudinary Moderation](https://cloudinary.com/documentation/cloudinary_moderation.md) — distinct from the per-asset [moderation flag](moderate-upload.md) this SDK sets |
| Frontend rendering, responsive images, upload UI | [frontend SDKs](https://cloudinary.com/documentation/frontend_sdks.md), [Upload Widget](https://cloudinary.com/documentation/upload_widget.md) |
