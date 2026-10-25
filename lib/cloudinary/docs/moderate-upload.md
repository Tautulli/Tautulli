# Moderate an upload

## When to use

Content uploaded by users must be reviewed before it is delivered. Moderation in
Cloudinary is stateful: an asset carries a moderation status, and your application is
responsible for delivering approved assets only.

**By default, `pending` does not block delivery.** A moderated asset is deliverable and
visible in the Media Library from the moment it is uploaded — the status is metadata you
gate on in your own code.

Blocking delivery of non-approved assets can be configured for your product environment.
It is not an upload parameter — contact Cloudinary support. Gate on the status in your
code regardless.

For platform-wide moderation with review queues and rules, see
[Cloudinary Moderation](https://cloudinary.com/documentation/cloudinary_moderation.md) —
distinct from the per-asset flag this SDK sets.

## Complete flow (manual review queue)

```python
import cloudinary
import cloudinary.api
import cloudinary.uploader

# Configuration is read from CLOUDINARY_URL automatically.


def main():
    result = cloudinary.uploader.upload(
        "https://res.cloudinary.com/demo/image/upload/sample.jpg",
        moderation="manual",              # hold for review
        folder="user-uploads",
    )

    # The upload result carries a `moderation` list, not a `moderation_status` key.
    print(result["moderation"])          # [{'kind': 'manual', 'status': 'pending'}]
    public_id = result["public_id"]

    # Later: list what is waiting for review.
    pending = cloudinary.api.resources_by_moderation("manual", "pending", max_results=100)
    print(len(pending["resources"]))

    # Record the verdict (or "rejected"); your code gates delivery on it.
    approved = cloudinary.api.update(public_id, moderation_status="approved")
    print(approved["moderation_status"])  # 'approved'
    print(approved["moderation"])         # [{'kind': 'manual', 'status': 'approved', 'updated_at': ...}]

    return approved


if __name__ == "__main__":
    try:
        main()
    except cloudinary.exceptions.Error as error:
        print("Moderation flow failed: {0}".format(error))
        raise SystemExit(1)
```

## Result fields to keep

Store `asset_id` and `public_id` alongside your own review record.

Which field holds the status depends on the call: the **upload** result exposes only the
`moderation` list (`[{"kind": "manual", "status": "pending"}]`), while
`cloudinary.api.resource()` and `cloudinary.api.update()` return both `moderation` and a
flat `moderation_status`. Read `result["moderation"][0]["status"]` if you want one
expression that works everywhere.

The statuses are `queued`, `pending`, `approved`, `rejected`, and `aborted`. None of them
block delivery by default — gate on the status in your own code.

## Automated moderation

Pass an add-on name instead of `manual` to get an automated verdict.

**Prerequisite — a human has to do this, not your code.** Every value below except
`manual` requires its add-on to be registered on the account first, from the
[Add-ons page](https://cloudinary.com/documentation/cloudinary_add_ons.md) in the console.
Some third-party add-ons also require reviewing and accepting the provider's terms of
service as part of registration. Neither step has an API; until both are done the add-on
value is rejected at upload. `manual` needs no add-on and no terms accepted, which is why
the flow above uses it.

| Value | Moderates | Add-on |
|---|---|---|
| `aws_rek` | images | Amazon Rekognition AI Moderation |
| `aws_rek_video` | video | Amazon Rekognition Video Moderation |
| `google_video_moderation` | video | Google AI Video Moderation |
| `webpurify` | images | WebPurify Image Moderation |
| `perception_point` | any asset | Perception Point Malware Detection |
| `duplicate:<threshold>` | images | Cloudinary Duplicate Image Detection |

```python
cloudinary.uploader.upload(source, moderation="aws_rek")            # images
cloudinary.uploader.upload(source, moderation="google_video_moderation",
                           resource_type="video")                    # video
cloudinary.uploader.upload(source, moderation="perception_point")    # malware
```

Combine several with a pipe — the order is the order they run in, and `manual` must be
last (`"aws_rek|duplicate:0.9|manual"`). The first moderation starts as `pending` and the
rest as `queued`; if one rejects, the remaining become `aborted` and the asset's final
status is `rejected`. Always set a `notification_url` when requesting several.

Automated moderation is asynchronous: the upload returns `pending` and the verdict lands
seconds to minutes later. Do not block on it — set `notification_url` and react to the
webhook, or poll `cloudinary.api.resource(public_id)`. An asset may sit in `queued` before
the add-on reaches it.

Assert on shape, not on verdicts. Model output varies between runs and versions, so check
that a `moderation` entry exists with a known status value rather than expecting a
specific score.

## Combining moderation with tagging

Moderation answers "may this be shown"; the analysis add-ons answer "what is in it". They
compose in one call:

```python
cloudinary.uploader.upload(
    source,
    moderation="aws_rek",
    categorization="google_tagging",
    auto_tagging=0.7,          # apply tags above this confidence
    notification_url="https://example.com/cloudinary-hook",
)
```

## Troubleshooting

- A pending asset delivers instead of 404ing — that is the default behavior, not a bug.
  Gate on `moderation_status` in your own code, or contact support to have non-approved
  assets blocked for your product environment.
- `You don't have an active subscription for <add-on>` (raised as `RateLimited`, not a
  permission error) — the named add-on is not enabled on this account.
  `moderation="manual"` needs no subscription and is the way to test the flow.
- `moderation_status` stays `pending` forever with an automated kind — the add-on is
  queued or failed; check the `moderation` entry for an error, and confirm the add-on
  supports the resource type.
- `Illegal moderation status: <value>` on update — the accepted values are `approved`
  and `rejected`.
- `resources_by_moderation` returns nothing — the `kind` argument must match the
  moderation used at upload (`manual`, `aws_rek`, ...), not the status.
- Rejected assets still occupy storage. Delete them with `cloudinary.uploader.destroy()`
  if you do not need an audit trail.

## Related

- Runnable example: `examples/moderate-upload.py`
- [Upload an image](upload-image.md)
- [Search and manage assets](search-and-manage-assets.md) — finding and deleting what you
  moderated.
- [Moderation add-ons](https://cloudinary.com/documentation/moderate_assets.md)
