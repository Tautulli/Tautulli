---
title: Exporter Guide
sidebar_position: 11
---

## Contents

- [Introduction](#introduction)
- [File Formats](#file-formats)
  - [Export Individual Files](#export-individual-files)
- [Metadata and Media Info Exports](#metadata-and-media-info-exports)
  - [Metadata and Media Info Export Levels](#metadata-and-media-info-export-levels)
  - [Custom Fields](#custom-fields)
- [Resource Exports](#resource-exports)
  - [Resource Export Levels](#resource-export-levels)
- [Media Type Fields](#media-type-fields)
  - [Movies](#movies)
  - [Shows](#shows)
  - [Seasons](#seasons)
  - [Episodes](#episodes)
  - [Artists](#artists)
  - [Albums](#albums)
  - [Tracks](#tracks)
  - [Photo Albums](#photo-albums)
  - [Photos](#photos)
  - [Clips](#clips)
  - [Collections](#collections)
  - [Playlists](#playlists)

---

## Introduction

The exporter feature of Tautulli allows you to export metadata and media info from your Plex library. The exporter can be accessed from various locations:

1. On any library page from the [Collections](./images/exporter_library_collections.png), [Playlists](./images/exporter_library_playlists.png), or [Export](./images/exporter_library_export.png) tabs. This will allow you to export all of your collections, playlists or all items for any library on your Plex server.
1. On any user page from the [Playlists](./images/exporter_user_playlists.png) tab. This will allow you to export all of a user's playlists for any user on your Plex server.
1. On any media info page from the [Export](./images/exporter_media_info.png) tab. This will allow you to export the metadata for any single media item on your Plex server.

Clicking on the export button on any of those pages will open up the [export metadata modal](./images/exporter_modal.png) where you can customize your export. All the customization options are described in the sections below.

The [metadata exports table](./images/exporter_table.png) on the library, user, or media info page will list all your previous exports and allow you to view or download a copy of the exported files. The download will return the exported file if only a single data file is exported, otherwise the download will return a `zip` archive containing all the exported data files and images. A progress percentage will be shown in the downloads column while an export is in progress. Exports are processed in the background so you may leave the page and check back later when it is complete.

* **Note:** The exporter only exports metadata. There is no import feature available in Tautulli.


## File Formats

Metadata can be exported to various file formats. Notes about each file format is listed in the following table.

| File Format | Description |
| :---: | --- |
| `csv` | Export a comma-separated values file.<ul><li>**Note:** Each row in the `csv` file is unique so there may be multiple rows for the same media item (e.g. each `genres.tag` will be on it's own row so a single movie may have multiple rows).</li></ul> |
| `json` | Export a `json` format file. |
| `xml` | Export a `xml` format file.<ul><li>**Note:** The `xml` export is not the same as the [Plex XML data](https://support.plex.tv/articles/201998867-investigate-media-information-and-formats/).</li></ul> |
| `m3u` | Only export a `m3u` playlist file with the paths to all the media items without any additional metadata.<ul><li>**Note:** All files will be added to the playlist if there are multiple parts/versions.</li><li>**Note:** Export level selections are not allowed.</li></ul> |


### Export Individual Files

Enable this option to export one file for each collection/playlist/library item instead of a single file containing all items.

* **Note:** This option is only available when exporting collections, playlists or all items from the library or user page.


## Metadata and Media Info Exports

The exporter has several predefined export levels. The export levels are separated into _metadata levels_ which include fields about the metadata of the item (e.g. `title`, `year`, `summary`, etc.) and _media info levels_ which include fields about the media file (e.g. `media.videoResolution`, `media.audioCodec`, `media.hdr`, etc.). The metadata level and media info level can be different, and the same level *does not* need to be selected for both. Higher levels will include all the fields from the lower levels. The fields that will be exported for each level are listed in the [Media Type Fields](#media-type-fields) sections below.


### Metadata and Media Info Export Levels

| Metadata Export Level | Name | Description |
| :---: | --- | --- |
| **Level 0** | None / Custom | No metadata will be exported. Specify custom metadata fields to select which fields to export. |
| **Level 1** | Basic Metadata | Only basic metadata such as `title`, `year`, `summary`, etc. |
| **Level 2** | Extended Metadata | Tags such as `genres.tag`, `collections.tag`, `roles.tag`, etc. |
| **Level 3** | Advanced Metadata | Fields such as Plex API keys for `art`, `thumb`, `theme`, etc. |
| **Level 9** | All Metadata | All metadata will be exported. |

| Media Info Export Level | Name | Description |
| :---: | --- | --- |
| **Level 0** | None / Custom | No media info will be exported. Specify custom media info fields to select which fields to export. |
| **Level 1** | Basic Media Info| Only basic media info such as `media.bitrate`, `media.videoCodec`, `media.audioChannels`, etc. |
| **Level 2** | Extended Media Info | Fields for the specific media file part such as `media.parts.size`, `media.parts.duration`, etc. |
| **Level 3** | Advanced Media Info | Fields for specific streams inside a media file part such as <br>`media.parts.videoStreams.refFrames`, `media.parts.audioStreams.samplingRate`, `media.parts.subtitleStreams.language`, etc. |
| **Level 9** | All Media Info | All media info will be exported. |


### Custom Fields

[Custom fields](./images/exporter_custom_fields.png) can be added *in addition* to any export level. All fields from the selected metadata or media info level *plus* the custom fields will be exported. Start typing in the custom field box to search for a specific field to add. Some fields will be disabled to indicate that it is already included in the selected export level. All the available fields are listed in the [Media Type Fields](#media-type-fields) sections below.

* **Note:** Custom fields for child media types are prefixed with the media type and separated with periods (`.`). The periods also delineate the tree structure in the `json` or `xml` file.
  * e.g. The `seasons.episodes.title` field will export the episode title for all seasons and all episodes for a TV show.

* **Note:** For [Collections](#collections) and [Playlists](#playlists), the `items` prefix can be different media types depending on the context. Refer to the [Media Type Fields](#media-type-fields) sections below for all the possible media types.
  * e.g. The `items.title` field will be the movie title in a movie collection or TV show titles in a TV show collection.


## Resource Exports

[Image and theme resources](./images/exporter_images.png) can be exported along with the metadata. Resources will be exported to a `.resources` folder alongside the data file with the following extensions:
  * Posters and Covers: `.thumb.jpg`
  * Background Artwork: `.art.jpg`
  * Logos: `.logo.png`
  * Square Art: `.squareArt.jpg`
  * Theme Music: `.theme.mp3`
  
When downloading an export from the [metadata exports table](./images/exporter_table.png), the resources will be included in a `zip` archive with the data file.

* **Warning:** Exporting resources may take a long time!

* **Note:** Resources will only be exported by the selected resource export level for the following supported media types:
  * Movies, shows, seasons, artists, albums, photo albums, collections, playlists, and collection or playlist items of those types
  * Theme music is only exported for movies, shows, artists, and collections
* **Note:** Additional images for any media type that has these fields in [Media Type Fields](#media-type-fields) can be exported by adding the following custom metadata fields:
  * Posters and Covers: `thumbFile`
  * Background Artwork: `artFile`
  * Logos: `logoFile`
  * Square Art: `squareArtFile`
  * Theme Music: `themeFile`
  
  Adding the custom field will export _all_ resources of that type regardless of the selected resource export level.
  * e.g. Adding `episodes.thumbFile` to the custom metadata fields will export all episode thumbnails even though it is not included in the supported resource export media types.

### Resource Export Levels

| Poster and Cover Image Export Level | Name | Description | 
| :---: | --- | --- |
| **Level 0** | None / Custom | No poster/cover images will be exported. Specific posters/covers can be exported by adding `thumbFile` to the custom metadata fields. |
| **Level 1** | Uploaded and Selected Posters and Covers Only | Only custom poster/cover images which have been uploaded manually and are currently selected as the active poster/cover.
| **Level 2** | Selected and Locked Posters and Covers Only | Only currently selected poster/cover images which have been changed from the default poster/cover.
| **Level 9** | All Selected Posters and Covers | All poster/cover images for the supported media types. |

| Background Artwork Image Export Level |  Name | Description | 
| :---: | --- | --- |
| **Level 0** | None / Custom | No background artwork images will be exported. Specific background art can be exported by adding `artFile` to the custom metadata fields. |
| **Level 1** | Uploaded and Selected Artwork Only | Only custom background artwork images which have been uploaded manually and are currently selected as the active artwork. |
| **Level 2** | Selected and Locked Artwork Only | Only currently selected background artwork images which have been changed from the default artwork. |
| **Level 9** | All Selected Artwork | All background artwork images for the supported media types. |

| Logo Image Export Level |  Name | Description | 
| :---: | --- | --- |
| **Level 0** | None / Custom | No logo images will be exported. Specific logos can be exported by adding `logoFile` to the custom metadata fields. |
| **Level 1** | Uploaded and Selected Logos Only | Only custom logo images which have been uploaded manually and are currently selected as the active artwork. |
| **Level 2** | Selected and Locked Logos Only | Only currently selected logo images which have been changed from the default logo. |
| **Level 9** | All Selected Logos | All logo images for the supported media types. |

| Square Art Image Export Level |  Name | Description | 
| :---: | --- | --- |
| **Level 0** | None / Custom | No square art images will be exported. Specific square art can be exported by adding `squareArtFile` to the custom metadata fields. |
| **Level 1** | Uploaded and Selected Square Art Only | Only custom square art images which have been uploaded manually and are currently selected as the active artwork. |
| **Level 2** | Selected and Locked Square Art Only | Only currently selected square art images which have been changed from the default square art. |
| **Level 9** | All Selected Square Art | All square art images for the supported media types. |

| Theme Music Export Level |  Name | Description | 
| :---: | --- | --- |
| **Level 0** | None / Custom | No theme music will be exported. Specific theme music can be exported by adding `themeFile` to the custom metadata fields. |
| **Level 1** | Uploaded and Selected Themes Only | Only custom theme music which has been uploaded manually and is currently selected as the active theme music. |
| **Level 2** | Selected and Locked Themes Only | Only currently selected theme music which have been changed from the default theme music. |
| **Level 9** | All Selected Themes | All theme music for the supported media types. |

## Media Type Fields

<!-- generate-docs.py replaces this line with the field tables from build_export_docs() in plexpy/exporter.py. -->
