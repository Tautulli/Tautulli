# Organize and share collections

## When to use

Grouping existing assets into a named set, and sharing that set through a public link.

A collection references assets; it does not move, copy, or change them. Pick the right
tool:

- **Collection** (`cloudinary.collections`) — a curated set you name, list, and share as a
  public page. An asset can be in many collections.
- **Tag** (`uploader.add_tag`) — a label for filtering and bulk operations. No sharing.
- **Folder** (`api.create_folder`) — where an asset lives. An asset has exactly one.
- **Search** (`cloudinary.Search`) — a one-off query. Nothing is saved.

There are two types of collection, fixed at creation:

- **manual** (the default) — holds exactly the assets you add and remove.
- **dynamic** — holds whatever matches a saved search expression, and updates itself as
  assets start or stop matching. You cannot add or remove assets by hand.

## Rules

- `cloudinary.collections` must be imported explicitly. `import cloudinary` alone does not
  load it.
- Every response wraps its payload in `"data"`: `result["data"]["id"]`, not `result["id"]`.
- Add and remove assets by `asset_id`. A `public_id` fails with `NotFound: Error 404 -
  Unknown resource`.
- Store the collection `id` and the public page `id`. Every other call takes them.
- Never pass `None` as an ID. The SDK drops it from the URL and calls a different endpoint:
  `collections.collection(None)` lists all collections instead of failing.

## Complete flow

```python
import cloudinary
import cloudinary.exceptions
import cloudinary.uploader
from cloudinary import collections  # must be imported explicitly

# Configuration is read from CLOUDINARY_URL automatically.


def main():
    asset = cloudinary.uploader.upload("https://res.cloudinary.com/demo/image/upload/sample.jpg")

    collection = collections.create_collection(
        "Summer campaign",
        description="Approved images for the launch",
    )["data"]

    collections.add_collection_assets(collection["id"], [asset["asset_id"]])

    page = collections.create_collection_public_page(collection["id"], name="Launch preview")["data"]
    print(page["url"])  # https://collection.cloudinary.com/<cloud_name>/<page_id>

    return collection["id"], page["id"]


if __name__ == "__main__":
    try:
        main()
    except cloudinary.exceptions.Error as error:
        print("Collections call failed: {0}".format(error))
        raise SystemExit(1)
```

## Result fields to keep

| Call | Returns | Keep |
|---|---|---|
| `create_collection`, `update_collection`, `add_collection_assets`, `remove_collection_assets` | `{"data": {collection}}` | `data.id` |
| `collection` | `{"data": {collection}}`, plus `asset_count` and `cover_asset_url` | |
| `collections`, `collection_assets` | `{"data": [...], "total_count": N, "next_cursor": "..."}` | `next_cursor` |
| `create_collection_public_page`, `update_collection_public_page`, `collection_public_page` | `{"data": {page}}` | `data.id`, `data.url` |
| `collection_public_pages` | `{"data": [...]}` | |
| `delete_collection`, `delete_collection_public_page` | `{"message": "..."}` | |

A collection has `id`, `name`, `description`, `type`, `configuration`, `created_at`, and
`updated_at`. An asset in `collection_assets` has `asset_id`, `public_id`, `display_name`,
`resource_type`, `type`, `format`, `bytes`, `width`, `height`, `secure_url`, and
`created_at`.

## Managing assets in a manual collection

```python
collections.add_collection_assets(collection_id, ["asset_id_1", "asset_id_2"])
collections.add_collection_assets(collection_id, "asset_id_3")      # a single ID works too
collections.remove_collection_assets(collection_id, ["asset_id_1"])
```

Adding an asset that is already in the collection succeeds and changes nothing. Removing an
asset does not delete it.

Changes can take a few seconds to show up in `collection_assets`. For read-after-write, poll
until the asset appears instead of reading once.

## Dynamic collections

```python
collection = collections.create_collection(
    "Summer images",
    type="dynamic",
    configuration={"expression": "tags=summer AND resource_type:image"},
)["data"]

collections.update_collection(collection["id"], configuration={"expression": "tags=summer"})
```

The expression uses the same syntax as `cloudinary.Search`. A new dynamic collection takes a few seconds to populate.

## Listing and paging

```python
cursor = None
while True:
    page = collections.collection_assets(collection_id, sort_by="created_at desc",
                                         max_results=100, next_cursor=cursor)
    for asset in page["data"]:
        print(asset["asset_id"], asset["secure_url"])
    cursor = page.get("next_cursor")
    if not cursor:
        break
```

`next_cursor` is absent on the last page; read it with `.get()`. Send the same `sort_by` on
every page — a cursor is only valid for the sort it was issued with, and the server does not
reject a mismatch.

| Option | `collections` | `collection_assets` |
|---|---|---|
| `max_results` | 1-100, default 20 | 1-100, default 20 |
| `sort_by` | `name`, `created_at`, `updated_at` + `asc`/`desc`; default `updated_at desc` | `created_at`, `uploaded_at`, `public_id`, `display_name`, `bytes` + `asc`/`desc`; default `created_at desc` |
| `query` | matches a word in the name that starts with the text: `"sum"` matches "Summer campaign", `"umm"` does not | — |

Combine sort keys with commas: `sort_by="name asc, created_at desc"`.

## Sharing with public pages

```python
page = collections.create_collection_public_page(
    collection_id,
    name="Press kit",
    expires_at="2026-12-31T00:00:00Z",
    show_download_original_option=False,
    download_transformations=[{"name": "thumbnail_400", "types": ["image"]}],
    create_download_transformations=True,
)["data"]

collections.update_collection_public_page(collection_id, page["id"], name="Press kit (final)")
collections.collection_public_pages(collection_id)
collections.delete_collection_public_page(collection_id, page["id"])  # unpublish
```

Anyone with `page["url"]` can open the page until it expires or is unpublished. Unpublishing
does not change the collection or its assets.

- `download_transformations` must name existing named transformations, or the call fails with
  `BadRequest: Error 400 - Unknown named transformation '<name>'`. Create one with
  `cloudinary.api.create_transformation("thumbnail_400", "c_thumb,w_400")`.
- The first time a named transformation is offered for download, pass
  `create_download_transformations=True`. Without it the call fails with
  `BadRequest: Error 400 - Named transformation '<name>' is not available for download yet`.
- `types` (`["image"]`, `["video"]`, or omitted for both) is fixed the first time a name is
  offered for download, on any public page. Later requests must omit it or send the same
  list.
- `show_download_original_option` defaults to `True`.
- Restricting a page to specific viewers is update-only:
  `update_collection_public_page(..., protection_mode="email_otp", allowed_emails=[...],
  allowed_domains=[...])`. It needs the secured-sharing feature on your plan, or it fails
  with `NotAllowed: Error 403 - Feature is not allowed`.

## Updating and deleting

```python
collections.update_collection(collection_id, name="Summer campaign (final)")
collections.delete_collection(collection_id)
```

Updates change only the fields you pass: `name`, `description`, and, for dynamic collections,
`configuration`. The type cannot change; `type` is ignored on update. Deleting a collection
does not delete its assets.

## Authentication and plans

The methods work with an API key and secret, or with an OAuth token
(`cloudinary.config(oauth_token=...)`, scope `asset_management`).

Collections are a premium Assets Enterprise feature. On the Assets Free plan you can have at
most 3 collections, with up to 50 assets each. Dynamic collections and protected public pages
must be enabled for your product environment.

## Troubleshooting

- `NotAllowed: Error 403 - Cannot have more than 3 classic collections` — the plan's
  collection limit. Delete a collection or upgrade.
- `NotAllowed: Error 403 - Feature is not allowed` — dynamic collections or `email_otp`
  protection are not enabled for your product environment.
- ``NotFound: Error 404 - We can`t find a collection with this id ...`` — wrong or deleted
  collection ID.
- `NotFound: Error 404 - Unknown resource` from add or remove — you passed a `public_id`, or
  an `asset_id` that does not exist.
- `NotAcceptable: Error 406 - unsupported operation for dynamic collection` — you tried to add
  or remove assets in a dynamic collection. Change its expression instead.
- `BadRequest: Error 400 - dynamic collections require a configuration with a non-empty
  expression` — `type="dynamic"` without `configuration`.
- `BadRequest: Error 400 - configuration is only allowed for dynamic collections` —
  `configuration` on a manual collection.
- `BadRequest: Error 400 - Unknown named transformation ...` or `... is not available for
  download yet` — see [Sharing with public pages](#sharing-with-public-pages).
- `BadRequest: Error 400 - invalid sort_by field ...` or `... max_results ...` — see the
  options table above.
- An asset you just added is missing from `collection_assets` — wait a few seconds and read
  again.
- A call returned every collection instead of one — the ID was `None`.

## Related

- Runnable example: `examples/organize-and-share-collections.py`
- [Search and manage assets](search-and-manage-assets.md) — finding the `asset_id` values to
  add, and the expression syntax for dynamic collections.
- [Import and call the SDK](import-and-call.md)
