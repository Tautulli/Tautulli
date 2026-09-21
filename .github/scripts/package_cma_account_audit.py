"""Build the reviewed CMA account-audit YouTrack app archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile


APP_FILES = ("manifest.json", "entity-extensions.json", "account-sync.js")
EXPECTED_GLOBAL_PROPERTIES = {
    "cmaMemberNotificationReservedAt": "integer",
    "cmaMemberNotificationCycleId": "string",
    "cmaMemberNotificationPlexUserId": "string",
    "cmaMemberNotificationReservations": "string",
}


def canonical_bytes(path: Path) -> bytes:
    """Return platform-independent UTF-8 bytes for reviewed text sources."""
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def validate_declarations(source: Path) -> None:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("name") != "cma-account-audit":
        raise SystemExit("The account-audit app identity must remain cma-account-audit")
    if manifest.get("version") != "1.3.5":
        raise SystemExit("The reviewed account-audit app version must be 1.3.5")
    if manifest.get("minYouTrackVersion") != "2025.3.0":
        raise SystemExit("The account-audit app must require global-storage support")

    declaration = json.loads(
        (source / "entity-extensions.json").read_text(encoding="utf-8")
    )
    extensions = declaration.get("entityTypeExtensions")
    if not isinstance(extensions, list) or len(extensions) != 1:
        raise SystemExit("Expected exactly one account-audit entity type extension")
    if extensions[0].get("entityType") != "AppGlobalStorage":
        raise SystemExit("Notification budget properties must extend AppGlobalStorage")
    properties = extensions[0].get("properties")
    actual = (
        {name: value.get("type") for name, value in properties.items()}
        if isinstance(properties, dict)
        else {}
    )
    if actual != EXPECTED_GLOBAL_PROPERTIES:
        raise SystemExit(
            "Notification budget declaration changed: "
            f"expected {EXPECTED_GLOBAL_PROPERTIES}, found {actual}"
        )


def build_archive(source: Path, destination: Path) -> None:
    missing = [name for name in APP_FILES if not (source / name).is_file()]
    if missing:
        raise SystemExit("Missing account-audit app files: " + ", ".join(missing))

    actual_scripts = sorted(path.name for path in source.glob("*.js"))
    if actual_scripts != ["account-sync.js"]:
        raise SystemExit(
            "Account-audit production script inventory changed; expected "
            f"['account-sync.js'], found {actual_scripts}"
        )

    validate_declarations(source)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in APP_FILES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, canonical_bytes(source / name))

    with zipfile.ZipFile(destination, mode="r") as archive:
        if tuple(archive.namelist()) != APP_FILES:
            raise SystemExit("Account-audit archive root inventory is incorrect")
        bad_entry = archive.testzip()
        if bad_entry:
            raise SystemExit(f"Archive integrity check failed for {bad_entry}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("youtrack-app/cma-account-audit"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/cma-account-audit.zip"),
    )
    args = parser.parse_args()
    build_archive(args.source.resolve(), args.output.resolve())
    print(args.output)


if __name__ == "__main__":
    main()
