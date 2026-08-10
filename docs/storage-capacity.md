# Storage Capacity

The **Storage** section on the Tautulli homepage shows how much space is left on the
filesystems holding your Plex media.

## What it shows

One card per filesystem, each with:

* the mount point (or drive letter, or UNC share) of the filesystem
* used, free and total space
* a usage bar, which turns orange above 85% and red above 95%
* the Plex libraries stored on that filesystem

Capacity is read from the operating system. Tautulli never scans or walks the media
folders, so the lookup costs one system call per filesystem regardless of library size.
The result is cached for 5 minutes.

The section is only shown to admin users, and can be turned off or reordered under
*Settings → Homepage → Sections*.

## How storage locations are determined

Tautulli already asks the Plex server for the library list, and that response includes
each library's folders. No extra configuration is needed:

```
Plex library  ->  library folder  ->  mount point  ->  filesystem capacity
```

Libraries that live on the same filesystem are grouped into a single card so the space is
not counted more than once. For example:

```
Movies   /mnt/media/movies
TV       /mnt/media/tv          ->   one card for /mnt/media
Music    /mnt/media/music
```

Filesystems are identified by their device id rather than by path, so bind mounts and
other aliases of the same filesystem are also grouped together. Libraries on separate
drives get separate cards:

```
Movies   D:\Movies              ->   one card for D:\
TV       E:\TV                  ->   one card for E:\
```

## Limitations with remote Plex servers

Plex reports the paths as they exist on the machine running Plex. If Plex and Tautulli are
on different machines, those paths usually do not exist from Tautulli's point of view, and
there is no way for Tautulli to inspect them remotely — the Plex API does not expose
filesystem capacity.

When this happens the affected libraries are grouped into a single **Unavailable** card
rather than being hidden or reported as an error. The rest of the homepage is unaffected;
a path that cannot be inspected never raises.

## Docker and container considerations

The same applies to containers. The Plex container might mount your media at `/data/media`
while the Tautulli container mounts the same storage at `/mnt/media`. Tautulli can only
report on paths that are mounted into its own container.

To make a filesystem visible to Tautulli:

1. Mount the media into the Tautulli container (read-only is fine, for example
   `-v /mnt/media:/mnt/media:ro`).
2. Add a path mapping if the mount point differs from the path Plex reports.

## Path mappings

Path mappings are optional and only needed when the path Plex reports is not the path
Tautulli sees. Configure them under *Settings → Homepage → Storage*, one per line, as the
Plex path, a vertical bar, and the matching path on the Tautulli host:

```
/data/media|/mnt/media
```

With that mapping, a Plex library at `/data/media/movies` is inspected at
`/mnt/media/movies`. The card still shows the paths as Plex reports them.

Mappings apply to a path and everything beneath it. If several mappings match, the most
specific one wins. Windows and POSIX separators can be mixed freely, so mapping a Windows
Plex path to a Linux Tautulli path works:

```
D:\Media|/mnt/media
```

## API

Storage information is available through the API:

```
/api/v2?apikey=<apikey>&cmd=get_storage_info
```

Pass `refresh=true` to bypass the 5 minute cache. The command takes no path parameter —
only the folders reported by Plex, optionally rewritten by the configured path mappings,
are ever inspected. Byte values are returned raw; the units shown on the homepage are
formatted for display only.

```json
[
  {
    "mount_point": "/mnt/media",
    "paths": ["/mnt/media/movies", "/mnt/media/tv"],
    "libraries": [
      {"section_id": 1, "section_name": "Movies", "section_type": "movie"},
      {"section_id": 2, "section_name": "TV Shows", "section_type": "show"}
    ],
    "total_bytes": 48003031040000,
    "used_bytes": 36883236552704,
    "free_bytes": 11119794487296,
    "percent_used": 76.8,
    "status": "ok"
  }
]
```

An entry with `"status": "unavailable"` has `null` for the byte values and the mount point.
