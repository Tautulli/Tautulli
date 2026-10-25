# Use structured metadata

## When to use

Attaching typed, validated fields to assets — SKU, campaign, expiry date, category — and
searching on them.

Structured metadata differs from the other two ways to label an asset:

- **Tags** — a flat list of strings. Cheap, unvalidated, good for grouping.
- **Context** — arbitrary key/value pairs per asset. No schema, no validation.
- **Structured metadata** — fields you define once on the account, with a type, optional
  validation, and (for lists) a fixed set of allowed values.

## Complete flow

Define the field once, then set values per asset:

```python
import cloudinary
import cloudinary.api
import cloudinary.uploader

# Configuration is read from CLOUDINARY_URL automatically.


def main():
    # 1. Define the field on the account (once, not per upload).
    cloudinary.api.add_metadata_field({
        "external_id": "sku",
        "label": "SKU",
        "type": "string",
        "mandatory": False,
    })

    # 2. Set a value at upload time.
    result = cloudinary.uploader.upload(
        "https://res.cloudinary.com/demo/image/upload/sample.jpg",
        public_id="products/leather-bag",
        metadata={"sku": "BAG-001"},
    )
    print(result["metadata"])   # {'sku': 'BAG-001'}

    # 3. Or set it later, on assets that already exist.
    cloudinary.uploader.update_metadata({"sku": "BAG-002"}, ["products/leather-bag"])

    # 4. Search on it.
    found = cloudinary.Search().expression('metadata.sku="BAG-002"').execute()
    print(found["total_count"])

    return result


if __name__ == "__main__":
    try:
        main()
    except cloudinary.exceptions.Error as error:
        print("Metadata flow failed: {0}".format(error))
        raise SystemExit(1)
```

## Result fields to keep

Values come back under `metadata`, keyed by `external_id`. Keep the `external_id` strings
in your own code as constants — they are the contract between your application and the
account schema, and renaming a field's `label` does not change them.

## Field types

```python
cloudinary.api.add_metadata_field({"external_id": "notes", "label": "Notes", "type": "string"})
cloudinary.api.add_metadata_field({"external_id": "weight", "label": "Weight", "type": "integer"})
cloudinary.api.add_metadata_field({"external_id": "expires", "label": "Expires", "type": "date"})

# A single choice from a fixed list.
cloudinary.api.add_metadata_field({
    "external_id": "category",
    "label": "Category",
    "type": "enum",
    "datasource": {"values": [{"external_id": "bags", "value": "Bags"},
                              {"external_id": "shoes", "value": "Shoes"}]},
})

# Multiple choices from a fixed list.
cloudinary.api.add_metadata_field({
    "external_id": "channels", "label": "Channels", "type": "set",
    "datasource": {"values": [{"external_id": "web", "value": "Web"},
                              {"external_id": "print", "value": "Print"}]},
})
```

Dates are `YYYY-MM-DD` strings. For `enum` and `set`, the value you assign is the
option's `external_id`, not its display `value`.

## Managing the schema

```python
cloudinary.api.list_metadata_fields()
cloudinary.api.metadata_field_by_field_id("sku")
cloudinary.api.update_metadata_field("sku", {"label": "Product SKU"})
cloudinary.api.update_metadata_field_datasource("category", [{"external_id": "belts", "value": "Belts"}])
cloudinary.api.delete_metadata_field("sku")
```

Deleting a field hides it from assets but is not instant across the account; re-creating
the same `external_id` afterwards fails with `external id <name> already exists` while the
old one is still being removed.

Mandatory fields with a `default_value` apply to **new** uploads only. Adding a mandatory
field does not retroactively populate existing assets, and it will cause uploads that omit
it to fail unless a default is set.

## Reading values back

`cloudinary.api.resource()` includes a `metadata` dictionary. Search results omit it
unless you ask:

```python
cloudinary.api.resource("products/leather-bag")["metadata"]   # {'sku': 'BAG-002', ...}
cloudinary.Search().expression("tags=catalog").with_field("metadata").execute()
```

## Troubleshooting

- `external id <name> already exists` — the field is already defined on the account; use
  `update_metadata_field` instead of adding it again.
- `Metadata External IDs do not exist: ["<name>"]` — the key in your `metadata` dict is
  not a defined field. Define the field first; values for unknown fields are rejected, not
  ignored.
- `'<value>' is not valid for field '<name>'` on an `enum` or `set` — you passed the
  display `value` (`"Bags"`) instead of the option's `external_id` (`"bags"`).
- Search finds nothing immediately after a write — the search index lags by a few seconds.
  Both `metadata.sku="BAG-001"` and the unquoted form work; quote values containing
  spaces.
- `metadata` missing from a search result — request it with `.with_field("metadata")`.
- An upload starts failing after a schema change — a newly mandatory field without a
  default. Give it a `default_value` or supply it on every upload.

## Related

- Runnable example: `examples/use-structured-metadata.py`
- [Search and manage assets](search-and-manage-assets.md) — searching on these fields.
- [Upload an image](upload-image.md)
- [Structured metadata reference](https://cloudinary.com/documentation/structured_metadata.md)
