# Search and manage assets

## When to use

Finding assets you have already uploaded, and reading, updating, organizing, or deleting
them.

Two different APIs do this, and picking the wrong one is the usual source of confusion:

- **Search** (`cloudinary.Search`) — query by expression across fields, tags, folders, and
  dates. This is what you want for "find the assets matching X".
- **Admin** (`cloudinary.api`) — read or change one asset, or list by a single axis
  (tag, prefix, folder). This is what you want for "do something to this asset".

## Complete flow

```python
import cloudinary
import cloudinary.api  # cloudinary.api must be imported explicitly

# Configuration is read from CLOUDINARY_URL automatically.


def main():
    result = (
        cloudinary.Search()
        .expression("resource_type:image AND tags=catalog")
        .sort_by("created_at", "desc")
        .max_results(30)
        .execute()
    )

    print(result["total_count"])          # 12 — matches, not the page size
    for asset in result["resources"]:
        print(asset["asset_id"], asset["public_id"], asset["secure_url"])

    return result


if __name__ == "__main__":
    try:
        main()
    except cloudinary.exceptions.Error as error:
        print("Search failed: {0}".format(error))
        raise SystemExit(1)
```

The fluent methods each return the same builder, so order does not matter; nothing is sent
until `.execute()`.

## Result fields to keep

`total_count` is the number of matches; `resources` holds one page of them. Store
`asset_id` for anything you need to reference later — it survives renames, `public_id`
does not. Keep the `public_id` too: delivery URLs, transformations, and the uploader
methods are all addressed by `public_id`, and there is no asset-id form of them.

## Paging through everything

Search pages with an opaque cursor, capped at 500 results per page:

```python
search = cloudinary.Search().expression("resource_type:image").max_results(500)
cursor = None

while True:
    result = search.next_cursor(cursor).execute()
    for asset in result["resources"]:
        print(asset["asset_id"])
    cursor = result.get("next_cursor")
    if not cursor:
        break
```

Never loop on `total_count` — it is an estimate for large result sets. Loop until
`next_cursor` is absent.

## Useful expressions

```text
tags=catalog AND resource_type:image        # tagged, images only
folder:products/*                           # a folder and everything under it
uploaded_at>1d AND bytes>1m                 # recent and large
format:mp4 AND duration>60                  # long videos
-tags=archived                              # exclude a tag
context.alt:bag*                             # prefix match in context metadata
```

Ask for extra fields explicitly — `context`, `tags`, and `metadata` are omitted by
default:

```python
cloudinary.Search().expression("tags=catalog").with_field("context").with_field("tags").execute()
```

## Reading and updating one asset

Prefer `asset_id` as the handle: it is immutable, so a rename or a move cannot break the
reference.

```python
import cloudinary.api

asset = cloudinary.api.resource_by_asset_id("abcdef0123456789abcdef0123456789")
print(asset["bytes"], asset["width"], len(asset["derived"]))
```

`cloudinary.api.resource("products/leather-bag")` is the `public_id` equivalent, and
`cloudinary.api.resources_by_asset_ids([...])` reads up to 100 at once.

Updating is `public_id`-only — there is no `update_by_asset_id`, so read the `public_id`
off the asset you just fetched rather than hardcoding it:

```python
cloudinary.api.update(
    asset["public_id"],
    tags=["catalog", "autumn"],
    context={"alt": "Brown leather shoulder bag"},
)
```

## Organizing

```python
import cloudinary.api
import cloudinary.uploader

cloudinary.api.create_folder("products/bags")
cloudinary.api.subfolders("products")

# rename_folder returns {"from": {...}, "to": {...}} — there is no "success" key.
cloudinary.api.rename_folder("products/bags", "products/handbags")

cloudinary.uploader.rename("products/leather-bag", "products/handbags/leather-bag")
cloudinary.uploader.add_tag("featured", ["products/handbags/leather-bag"])
cloudinary.api.tags(max_results=100)
```

## Deleting

```python
import cloudinary.api
import cloudinary.uploader

cloudinary.api.delete_resources_by_asset_ids([                          # up to 100
    "abcdef0123456789abcdef0123456789",
    "fedcba9876543210fedcba9876543210",
])
cloudinary.api.delete_resources(["id-a", "id-b"])                      # by public_id
cloudinary.api.delete_resources_by_prefix("temp/")                     # a whole prefix
cloudinary.api.delete_derived_resources([derived_id])                  # transformed copies only

cloudinary.uploader.destroy("products/leather-bag", invalidate=True)   # public_id only
```

`invalidate=True` purges the CDN as well as the origin, and only `uploader.destroy` takes
it — the batch deletes above accept `invalidate` as an option but identify assets in bulk.
Deletion is permanent unless the asset is backed up, in which case
`cloudinary.api.restore_by_asset_ids([asset_id])` (or `restore(["id"])` by `public_id`)
brings it back.

## Troubleshooting

- Search returns nothing but the asset exists — the expression is wrong, not the index.
  `tags=catalog` uses `=`, while `resource_type:image` uses `:`. Test with a bare
  `public_id:my-asset` first.
- A brand-new asset is missing from results — the search index is eventually consistent
  and lags an upload by a few seconds. Use `cloudinary.api.resource_by_asset_id()` with
  the `asset_id` the upload returned for read-after-write.
- `context` or `tags` missing from results — request them with `.with_field()`.
- `Rate limit exceeded` — the Admin API allows roughly 500 requests per hour on free
  plans. Prefer one Search call over many `resource()` calls, and batch deletes.
- `Invalid value for parameter next_cursor` — cursors expire and are not shareable
  between differing queries; restart the loop.
- `Query Error (at position N)` — an unsupported expression. Leading wildcards are
  rejected (`context.alt:*bag*` fails, `context.alt:bag*` works), and metadata matches
  use `:` rather than `=`.
- `Cannot find source folder` from `rename_folder` — the `from_path` does not exist, often
  because a previous run already renamed it.
- `Resource not found` on update or destroy — the wrong `resource_type` (`video`, `raw`)
  or `type` (`private`, `authenticated`); both default to image/upload.

## Related

- Runnable example: `examples/search-and-manage-assets.py`
- [Use structured metadata](use-structured-metadata.md) — typed fields you can search on.
- [Upload an image](upload-image.md)
- [Search API reference](https://cloudinary.com/documentation/search_api.md)
- [Admin API reference](https://cloudinary.com/documentation/admin_api.md)
