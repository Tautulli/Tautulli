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

### Movies

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `canNormalizeLoudness` |  |  |  | ✓ | ✓ |
| `chapterSource` |  |  |  | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `editionTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `enableCreditsMarkerGeneration` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `hasCreditsMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `hasPreviewThumbnails` |  |  |  | ✓ | ✓ |
| `hasVoiceActivity` |  |  |  | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `languageOverride` |  |  |  |  | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `originalTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `slug` |  |  |  |  | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `studio` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `tagline` |  | ✓ | ✓ | ✓ | ✓ |
| `theme` |  |  |  |  | ✓ |
| `themeFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `themeProvider` |  |  |  |  | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `useOriginalTitle` |  |  |  |  | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewOffset` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `chapters.end` |  |  |  | ✓ | ✓ |
| `chapters.id` |  |  |  |  | ✓ |
| `chapters.index` |  |  |  | ✓ | ✓ |
| `chapters.start` |  |  |  | ✓ | ✓ |
| `chapters.tag` |  |  |  | ✓ | ✓ |
| `chapters.thumb` |  |  |  | ✓ | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `countries.id` |  |  |  |  | ✓ |
| `countries.tag` |  |  | ✓ | ✓ | ✓ |
| `directors.id` |  |  |  |  | ✓ |
| `directors.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `genres.id` |  |  |  |  | ✓ |
| `genres.tag` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  | ✓ | ✓ | ✓ |
| `markers.end` |  |  | ✓ | ✓ | ✓ |
| `markers.final` |  |  | ✓ | ✓ | ✓ |
| `markers.first` |  |  | ✓ | ✓ | ✓ |
| `markers.id` |  |  |  |  | ✓ |
| `markers.start` |  |  | ✓ | ✓ | ✓ |
| `markers.type` |  |  | ✓ | ✓ | ✓ |
| `producers.id` |  |  |  |  | ✓ |
| `producers.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.id` |  |  |  |  | ✓ |
| `roles.role` |  |  | ✓ | ✓ | ✓ |
| `roles.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.thumb` |  |  |  |  | ✓ |
| `writers.id` |  |  |  |  | ✓ |
| `writers.tag` |  |  | ✓ | ✓ | ✓ |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  | ✓ | ✓ | ✓ | ✓ |
| `media.aspectRatio` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioChannels` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioCodec` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioProfile` |  | ✓ | ✓ | ✓ | ✓ |
| `media.bitrate` |  | ✓ | ✓ | ✓ | ✓ |
| `media.container` |  | ✓ | ✓ | ✓ | ✓ |
| `media.duration` |  | ✓ | ✓ | ✓ | ✓ |
| `media.has64bitOffsets` |  |  |  |  | ✓ |
| `media.hasVoiceActivity` |  |  |  |  | ✓ |
| `media.hdr` |  | ✓ | ✓ | ✓ | ✓ |
| `media.height` |  | ✓ | ✓ | ✓ | ✓ |
| `media.id` |  |  |  |  | ✓ |
| `media.isOptimizedVersion` |  | ✓ | ✓ | ✓ | ✓ |
| `media.optimizedForStreaming` |  |  |  |  | ✓ |
| `media.proxyType` |  |  |  |  | ✓ |
| `media.target` |  |  |  |  | ✓ |
| `media.title` |  |  |  |  | ✓ |
| `media.videoCodec` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoFrameRate` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoProfile` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoResolution` |  | ✓ | ✓ | ✓ | ✓ |
| `media.width` |  | ✓ | ✓ | ✓ | ✓ |
| `media.parts.accessible` |  |  |  |  | ✓ |
| `media.parts.audioProfile` |  |  | ✓ | ✓ | ✓ |
| `media.parts.container` |  |  | ✓ | ✓ | ✓ |
| `media.parts.deepAnalysisVersion` |  |  | ✓ | ✓ | ✓ |
| `media.parts.duration` |  |  | ✓ | ✓ | ✓ |
| `media.parts.exists` |  |  |  |  | ✓ |
| `media.parts.file` |  |  | ✓ | ✓ | ✓ |
| `media.parts.has64bitOffsets` |  |  |  |  | ✓ |
| `media.parts.hasPreviewThumbnails` |  |  | ✓ | ✓ | ✓ |
| `media.parts.hasThumbnail` |  |  |  |  | ✓ |
| `media.parts.id` |  |  |  |  | ✓ |
| `media.parts.indexes` |  |  | ✓ | ✓ | ✓ |
| `media.parts.key` |  |  |  |  | ✓ |
| `media.parts.optimizedForStreaming` |  |  | ✓ | ✓ | ✓ |
| `media.parts.packetLength` |  |  |  |  | ✓ |
| `media.parts.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.size` |  |  | ✓ | ✓ | ✓ |
| `media.parts.sizeHuman` |  |  | ✓ | ✓ | ✓ |
| `media.parts.syncItemId` |  |  |  |  | ✓ |
| `media.parts.syncState` |  |  |  |  | ✓ |
| `media.parts.videoProfile` |  |  | ✓ | ✓ | ✓ |
| `media.parts.audioStreams.audioChannelLayout` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitDepth` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitrate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitrateMode` |  |  |  |  | ✓ |
| `media.parts.audioStreams.canNormalizeLoudness` |  |  |  |  | ✓ |
| `media.parts.audioStreams.channels` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.duration` |  |  |  |  | ✓ |
| `media.parts.audioStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.gainOffset` |  |  |  |  | ✓ |
| `media.parts.audioStreams.id` |  |  |  |  | ✓ |
| `media.parts.audioStreams.index` |  |  |  |  | ✓ |
| `media.parts.audioStreams.key` |  |  |  |  | ✓ |
| `media.parts.audioStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.audioStreams.loudness` |  |  |  |  | ✓ |
| `media.parts.audioStreams.loudnessAnalysisVersion` |  |  |  |  | ✓ |
| `media.parts.audioStreams.lra` |  |  |  |  | ✓ |
| `media.parts.audioStreams.peak` |  |  |  |  | ✓ |
| `media.parts.audioStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.threshold` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
| `media.parts.audioStreams.visualImpaired` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.canAutoSync` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.container` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.forced` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.format` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.headerCompression` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.hearingImpaired` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.id` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.index` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.key` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.perfectMatch` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.providerTitle` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.score` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.selected` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.sourceKey` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.transient` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.type` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.userID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIBLCompatID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIBLPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIELPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVILevel` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIProfile` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIRPUPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIVersion` |  |  |  |  | ✓ |
| `media.parts.videoStreams.anamorphic` |  |  |  |  | ✓ |
| `media.parts.videoStreams.bitDepth` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.bitrate` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.cabac` |  |  |  |  | ✓ |
| `media.parts.videoStreams.chromaLocation` |  |  |  |  | ✓ |
| `media.parts.videoStreams.chromaSubsampling` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.codecID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codedHeight` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codedWidth` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorPrimaries` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorRange` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorSpace` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.colorTrc` |  |  |  |  | ✓ |
| `media.parts.videoStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.duration` |  |  |  |  | ✓ |
| `media.parts.videoStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.frameRate` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.frameRateMode` |  |  |  |  | ✓ |
| `media.parts.videoStreams.hasScalingMatrix` |  |  |  |  | ✓ |
| `media.parts.videoStreams.hdr` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.height` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.id` |  |  |  |  | ✓ |
| `media.parts.videoStreams.index` |  |  |  |  | ✓ |
| `media.parts.videoStreams.key` |  |  |  |  | ✓ |
| `media.parts.videoStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.videoStreams.level` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.pixelAspectRatio` |  |  |  |  | ✓ |
| `media.parts.videoStreams.pixelFormat` |  |  |  |  | ✓ |
| `media.parts.videoStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.refFrames` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.videoStreams.scanType` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.selected` |  |  |  |  | ✓ |
| `media.parts.videoStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.videoStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.videoStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.type` |  |  |  |  | ✓ |
| `media.parts.videoStreams.width` |  |  |  | ✓ | ✓ |

</details>


### Shows

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `audioLanguage` |  |  |  |  | ✓ |
| `autoDeletionItemPolicyUnwatchedLibrary` |  |  |  |  | ✓ |
| `autoDeletionItemPolicyWatchedLibrary` |  |  |  |  | ✓ |
| `childCount` |  | ✓ | ✓ | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `editionTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `enableCreditsMarkerGeneration` |  |  |  |  | ✓ |
| `episodeSort` |  |  |  |  | ✓ |
| `flattenSeasons` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `languageOverride` |  |  |  |  | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `network` |  | ✓ | ✓ | ✓ | ✓ |
| `originalTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `seasonCount` |  | ✓ | ✓ | ✓ | ✓ |
| `showOrdering` |  |  |  |  | ✓ |
| `slug` |  |  |  |  | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `studio` |  | ✓ | ✓ | ✓ | ✓ |
| `subtitleLanguage` |  |  |  |  | ✓ |
| `subtitleMode` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `tagline` |  | ✓ | ✓ | ✓ | ✓ |
| `theme` |  |  |  | ✓ | ✓ |
| `themeFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `themeProvider` |  |  |  |  | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `useOriginalTitle` |  |  |  |  | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewedLeafCount` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `genres.id` |  |  |  |  | ✓ |
| `genres.tag` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.id` |  |  |  |  | ✓ |
| `roles.role` |  |  | ✓ | ✓ | ✓ |
| `roles.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.thumb` |  |  |  |  | ✓ |
| `seasons` |  | ✓<br>Includes [Seasons](#seasons) Level 1 | ✓<br>Includes [Seasons](#seasons) Level 2 | ✓<br>Includes [Seasons](#seasons) Level 3 | ✓<br>Includes [Seasons](#seasons) Level 9 |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  |  |  |  |  |
| `seasons` |  | ✓<br>Includes [Seasons](#seasons) Level 1 | ✓<br>Includes [Seasons](#seasons) Level 2 | ✓<br>Includes [Seasons](#seasons) Level 3 | ✓<br>Includes [Seasons](#seasons) Level 9 |

</details>


### Seasons

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `audioLanguage` |  |  |  |  | ✓ |
| `editionTitle` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  |  |  |  | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentStudio` |  |  |  |  | ✓ |
| `parentTheme` |  |  |  | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `seasonNumber` |  | ✓ | ✓ | ✓ | ✓ |
| `slug` |  |  |  |  | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `subtitleLanguage` |  |  |  |  | ✓ |
| `subtitleMode` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewedLeafCount` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  |  |  | ✓ |
| `episodes` |  | ✓<br>Includes [Episodes](#episodes) Level 1 | ✓<br>Includes [Episodes](#episodes) Level 2 | ✓<br>Includes [Episodes](#episodes) Level 3 | ✓<br>Includes [Episodes](#episodes) Level 9 |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `episodes` |  | ✓<br>Includes [Episodes](#episodes) Level 1 | ✓<br>Includes [Episodes](#episodes) Level 2 | ✓<br>Includes [Episodes](#episodes) Level 3 | ✓<br>Includes [Episodes](#episodes) Level 9 |

</details>


### Episodes

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `canNormalizeLoudness` |  |  |  | ✓ | ✓ |
| `chapterSource` |  |  |  | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `editionTitle` |  |  |  |  | ✓ |
| `episodeNumber` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentArt` |  |  |  | ✓ | ✓ |
| `grandparentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentKey` |  |  |  | ✓ | ✓ |
| `grandparentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentTheme` |  |  |  | ✓ | ✓ |
| `grandparentThumb` |  |  |  | ✓ | ✓ |
| `grandparentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `hasCommercialMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `hasCreditsMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `hasIntroMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `hasPreviewThumbnails` |  |  |  | ✓ | ✓ |
| `hasVoiceActivity` |  |  |  | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  |  |  |  | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `parentYear` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `seasonEpisode` |  | ✓ | ✓ | ✓ | ✓ |
| `seasonNumber` |  | ✓ | ✓ | ✓ | ✓ |
| `slug` |  |  |  |  | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewOffset` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `chapters.end` |  |  |  | ✓ | ✓ |
| `chapters.id` |  |  |  |  | ✓ |
| `chapters.index` |  |  |  | ✓ | ✓ |
| `chapters.start` |  |  |  | ✓ | ✓ |
| `chapters.tag` |  |  |  | ✓ | ✓ |
| `chapters.thumb` |  |  |  | ✓ | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `directors.id` |  |  |  |  | ✓ |
| `directors.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  |  |  | ✓ |
| `markers.end` |  |  | ✓ | ✓ | ✓ |
| `markers.final` |  |  | ✓ | ✓ | ✓ |
| `markers.first` |  |  | ✓ | ✓ | ✓ |
| `markers.id` |  |  |  |  | ✓ |
| `markers.start` |  |  | ✓ | ✓ | ✓ |
| `markers.type` |  |  | ✓ | ✓ | ✓ |
| `producers.id` |  |  |  |  | ✓ |
| `producers.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.id` |  |  |  |  | ✓ |
| `roles.role` |  |  | ✓ | ✓ | ✓ |
| `roles.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.thumb` |  |  |  |  | ✓ |
| `writers.id` |  |  |  |  | ✓ |
| `writers.tag` |  |  | ✓ | ✓ | ✓ |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  | ✓ | ✓ | ✓ | ✓ |
| `media.aspectRatio` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioChannels` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioCodec` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioProfile` |  | ✓ | ✓ | ✓ | ✓ |
| `media.bitrate` |  | ✓ | ✓ | ✓ | ✓ |
| `media.container` |  | ✓ | ✓ | ✓ | ✓ |
| `media.duration` |  | ✓ | ✓ | ✓ | ✓ |
| `media.has64bitOffsets` |  |  |  |  | ✓ |
| `media.hasVoiceActivity` |  |  |  |  | ✓ |
| `media.hdr` |  | ✓ | ✓ | ✓ | ✓ |
| `media.height` |  | ✓ | ✓ | ✓ | ✓ |
| `media.id` |  |  |  |  | ✓ |
| `media.isOptimizedVersion` |  | ✓ | ✓ | ✓ | ✓ |
| `media.optimizedForStreaming` |  |  |  |  | ✓ |
| `media.proxyType` |  |  |  |  | ✓ |
| `media.target` |  |  |  |  | ✓ |
| `media.title` |  |  |  |  | ✓ |
| `media.videoCodec` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoFrameRate` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoProfile` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoResolution` |  | ✓ | ✓ | ✓ | ✓ |
| `media.width` |  | ✓ | ✓ | ✓ | ✓ |
| `media.parts.accessible` |  |  |  |  | ✓ |
| `media.parts.audioProfile` |  |  | ✓ | ✓ | ✓ |
| `media.parts.container` |  |  | ✓ | ✓ | ✓ |
| `media.parts.deepAnalysisVersion` |  |  | ✓ | ✓ | ✓ |
| `media.parts.duration` |  |  | ✓ | ✓ | ✓ |
| `media.parts.exists` |  |  |  |  | ✓ |
| `media.parts.file` |  |  | ✓ | ✓ | ✓ |
| `media.parts.has64bitOffsets` |  |  |  |  | ✓ |
| `media.parts.hasPreviewThumbnails` |  |  | ✓ | ✓ | ✓ |
| `media.parts.hasThumbnail` |  |  |  |  | ✓ |
| `media.parts.id` |  |  |  |  | ✓ |
| `media.parts.indexes` |  |  | ✓ | ✓ | ✓ |
| `media.parts.key` |  |  |  |  | ✓ |
| `media.parts.optimizedForStreaming` |  |  | ✓ | ✓ | ✓ |
| `media.parts.packetLength` |  |  |  |  | ✓ |
| `media.parts.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.size` |  |  | ✓ | ✓ | ✓ |
| `media.parts.sizeHuman` |  |  | ✓ | ✓ | ✓ |
| `media.parts.syncItemId` |  |  |  |  | ✓ |
| `media.parts.syncState` |  |  |  |  | ✓ |
| `media.parts.videoProfile` |  |  | ✓ | ✓ | ✓ |
| `media.parts.audioStreams.audioChannelLayout` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitDepth` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitrate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitrateMode` |  |  |  |  | ✓ |
| `media.parts.audioStreams.canNormalizeLoudness` |  |  |  |  | ✓ |
| `media.parts.audioStreams.channels` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.duration` |  |  |  |  | ✓ |
| `media.parts.audioStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.gainOffset` |  |  |  |  | ✓ |
| `media.parts.audioStreams.id` |  |  |  |  | ✓ |
| `media.parts.audioStreams.index` |  |  |  |  | ✓ |
| `media.parts.audioStreams.key` |  |  |  |  | ✓ |
| `media.parts.audioStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.audioStreams.loudness` |  |  |  |  | ✓ |
| `media.parts.audioStreams.loudnessAnalysisVersion` |  |  |  |  | ✓ |
| `media.parts.audioStreams.lra` |  |  |  |  | ✓ |
| `media.parts.audioStreams.peak` |  |  |  |  | ✓ |
| `media.parts.audioStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.threshold` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
| `media.parts.audioStreams.visualImpaired` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.canAutoSync` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.container` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.forced` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.format` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.headerCompression` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.hearingImpaired` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.id` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.index` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.key` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.perfectMatch` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.providerTitle` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.score` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.selected` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.sourceKey` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.transient` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.type` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.userID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIBLCompatID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIBLPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIELPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVILevel` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIProfile` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIRPUPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIVersion` |  |  |  |  | ✓ |
| `media.parts.videoStreams.anamorphic` |  |  |  |  | ✓ |
| `media.parts.videoStreams.bitDepth` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.bitrate` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.cabac` |  |  |  |  | ✓ |
| `media.parts.videoStreams.chromaLocation` |  |  |  |  | ✓ |
| `media.parts.videoStreams.chromaSubsampling` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.codecID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codedHeight` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codedWidth` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorPrimaries` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorRange` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorSpace` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.colorTrc` |  |  |  |  | ✓ |
| `media.parts.videoStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.duration` |  |  |  |  | ✓ |
| `media.parts.videoStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.frameRate` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.frameRateMode` |  |  |  |  | ✓ |
| `media.parts.videoStreams.hasScalingMatrix` |  |  |  |  | ✓ |
| `media.parts.videoStreams.hdr` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.height` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.id` |  |  |  |  | ✓ |
| `media.parts.videoStreams.index` |  |  |  |  | ✓ |
| `media.parts.videoStreams.key` |  |  |  |  | ✓ |
| `media.parts.videoStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.videoStreams.level` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.pixelAspectRatio` |  |  |  |  | ✓ |
| `media.parts.videoStreams.pixelFormat` |  |  |  |  | ✓ |
| `media.parts.videoStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.refFrames` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.videoStreams.scanType` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.selected` |  |  |  |  | ✓ |
| `media.parts.videoStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.videoStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.videoStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.type` |  |  |  |  | ✓ |
| `media.parts.videoStreams.width` |  |  |  | ✓ | ✓ |

</details>


### Artists

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `albumSort` |  |  |  |  | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `theme` |  |  |  |  | ✓ |
| `themeFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `themeProvider` |  |  |  |  | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `countries.id` |  |  |  |  | ✓ |
| `countries.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `genres.id` |  |  |  |  | ✓ |
| `genres.tag` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  |  |  | ✓ |
| `moods.id` |  |  |  |  | ✓ |
| `moods.tag` |  |  | ✓ | ✓ | ✓ |
| `similar.id` |  |  |  |  | ✓ |
| `similar.tag` |  |  | ✓ | ✓ | ✓ |
| `styles.id` |  |  |  |  | ✓ |
| `styles.tag` |  |  | ✓ | ✓ | ✓ |
| `albums` |  | ✓<br>Includes [Albums](#albums) Level 1 | ✓<br>Includes [Albums](#albums) Level 2 | ✓<br>Includes [Albums](#albums) Level 3 | ✓<br>Includes [Albums](#albums) Level 9 |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  |  |  |  |  |
| `albums` |  | ✓<br>Includes [Albums](#albums) Level 1 | ✓<br>Includes [Albums](#albums) Level 2 | ✓<br>Includes [Albums](#albums) Level 3 | ✓<br>Includes [Albums](#albums) Level 9 |

</details>


### Albums

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `hasSonicAnalysis` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `loudnessAnalysisVersion` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `musicAnalysisVersion` |  |  |  |  | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentTheme` |  |  |  |  | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `studio` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewedLeafCount` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `formats.id` |  |  |  |  | ✓ |
| `formats.tag` |  |  | ✓ | ✓ | ✓ |
| `genres.id` |  |  |  |  | ✓ |
| `genres.tag` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  | ✓ | ✓ | ✓ |
| `moods.id` |  |  |  |  | ✓ |
| `moods.tag` |  |  | ✓ | ✓ | ✓ |
| `styles.id` |  |  |  |  | ✓ |
| `styles.tag` |  |  | ✓ | ✓ | ✓ |
| `subformats.id` |  |  |  |  | ✓ |
| `subformats.tag` |  |  | ✓ | ✓ | ✓ |
| `tracks` |  | ✓<br>Includes [Tracks](#tracks) Level 1 | ✓<br>Includes [Tracks](#tracks) Level 2 | ✓<br>Includes [Tracks](#tracks) Level 3 | ✓<br>Includes [Tracks](#tracks) Level 9 |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `tracks` |  | ✓<br>Includes [Tracks](#tracks) Level 1 | ✓<br>Includes [Tracks](#tracks) Level 2 | ✓<br>Includes [Tracks](#tracks) Level 3 | ✓<br>Includes [Tracks](#tracks) Level 9 |

</details>


### Tracks

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `chapterSource` |  |  |  |  | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentArt` |  |  |  | ✓ | ✓ |
| `grandparentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentKey` |  |  |  | ✓ | ✓ |
| `grandparentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentTheme` |  |  |  |  | ✓ |
| `grandparentThumb` |  |  |  | ✓ | ✓ |
| `grandparentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `hasSonicAnalysis` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `musicAnalysisVersion` |  |  |  |  | ✓ |
| `originalTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  | ✓ | ✓ | ✓ | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingCount` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `skipCount` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `trackNumber` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewOffset` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `chapters.end` |  |  |  |  | ✓ |
| `chapters.id` |  |  |  |  | ✓ |
| `chapters.index` |  |  |  |  | ✓ |
| `chapters.start` |  |  |  |  | ✓ |
| `chapters.tag` |  |  |  |  | ✓ |
| `chapters.thumb` |  |  |  |  | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `genres.id` |  |  |  |  | ✓ |
| `genres.tag` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  |  |  | ✓ |
| `moods.id` |  |  |  |  | ✓ |
| `moods.tag` |  |  | ✓ | ✓ | ✓ |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioChannels` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioCodec` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioProfile` |  | ✓ | ✓ | ✓ | ✓ |
| `media.bitrate` |  | ✓ | ✓ | ✓ | ✓ |
| `media.container` |  | ✓ | ✓ | ✓ | ✓ |
| `media.duration` |  | ✓ | ✓ | ✓ | ✓ |
| `media.id` |  |  |  |  | ✓ |
| `media.title` |  |  |  |  | ✓ |
| `media.parts.accessible` |  |  |  |  | ✓ |
| `media.parts.audioProfile` |  |  | ✓ | ✓ | ✓ |
| `media.parts.container` |  |  | ✓ | ✓ | ✓ |
| `media.parts.deepAnalysisVersion` |  |  | ✓ | ✓ | ✓ |
| `media.parts.duration` |  |  | ✓ | ✓ | ✓ |
| `media.parts.exists` |  |  |  |  | ✓ |
| `media.parts.file` |  |  | ✓ | ✓ | ✓ |
| `media.parts.hasThumbnail` |  |  | ✓ | ✓ | ✓ |
| `media.parts.id` |  |  |  |  | ✓ |
| `media.parts.key` |  |  |  |  | ✓ |
| `media.parts.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.size` |  |  | ✓ | ✓ | ✓ |
| `media.parts.sizeHuman` |  |  | ✓ | ✓ | ✓ |
| `media.parts.syncItemId` |  |  |  |  | ✓ |
| `media.parts.syncState` |  |  |  |  | ✓ |
| `media.parts.audioStreams.albumGain` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.albumPeak` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.albumRange` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.audioChannelLayout` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitDepth` |  |  |  |  | ✓ |
| `media.parts.audioStreams.bitrate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitrateMode` |  |  |  |  | ✓ |
| `media.parts.audioStreams.channels` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.duration` |  |  |  |  | ✓ |
| `media.parts.audioStreams.endRamp` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.gain` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.id` |  |  |  |  | ✓ |
| `media.parts.audioStreams.index` |  |  |  |  | ✓ |
| `media.parts.audioStreams.key` |  |  |  |  | ✓ |
| `media.parts.audioStreams.language` |  |  |  |  | ✓ |
| `media.parts.audioStreams.languageCode` |  |  |  |  | ✓ |
| `media.parts.audioStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.audioStreams.loudness` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.lra` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.peak` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.profile` |  |  |  |  | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.startRamp` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
| `media.parts.audioStreams.visualImpaired` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.format` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.id` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.index` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.key` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.language` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.languageCode` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.minLines` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.provider` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.selected` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.timed` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.type` |  |  |  |  | ✓ |

</details>


### Photo Albums

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `composite` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `photoalbums` |  | ✓<br>Includes [Photo Albums](#photo-albums) Level 1 | ✓<br>Includes [Photo Albums](#photo-albums) Level 2 | ✓<br>Includes [Photo Albums](#photo-albums) Level 3 | ✓<br>Includes [Photo Albums](#photo-albums) Level 9 |
| `photos` |  | ✓<br>Includes [Photos](#photos) Level 1 | ✓<br>Includes [Photos](#photos) Level 2 | ✓<br>Includes [Photos](#photos) Level 3 | ✓<br>Includes [Photos](#photos) Level 9 |
| `clips` |  | ✓<br>Includes [Clips](#clips) Level 1 | ✓<br>Includes [Clips](#clips) Level 2 | ✓<br>Includes [Clips](#clips) Level 3 | ✓<br>Includes [Clips](#clips) Level 9 |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `photoalbums` |  | ✓<br>Includes [Photo Albums](#photo-albums) Level 1 | ✓<br>Includes [Photo Albums](#photo-albums) Level 2 | ✓<br>Includes [Photo Albums](#photo-albums) Level 3 | ✓<br>Includes [Photo Albums](#photo-albums) Level 9 |
| `photos` |  | ✓<br>Includes [Photos](#photos) Level 1 | ✓<br>Includes [Photos](#photos) Level 2 | ✓<br>Includes [Photos](#photos) Level 3 | ✓<br>Includes [Photos](#photos) Level 9 |
| `clips` |  | ✓<br>Includes [Clips](#clips) Level 1 | ✓<br>Includes [Clips](#clips) Level 2 | ✓<br>Includes [Clips](#clips) Level 3 | ✓<br>Includes [Clips](#clips) Level 9 |

</details>


### Photos

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `createdAtAccuracy` |  | ✓ | ✓ | ✓ | ✓ |
| `createdAtTZOffset` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  | ✓ | ✓ | ✓ | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `fields.locked` |  |  |  |  | ✓ |
| `fields.name` |  |  |  |  | ✓ |
| `tag.id` |  |  |  |  | ✓ |
| `tag.tag` |  |  | ✓ | ✓ | ✓ |
| `tag.title` |  |  | ✓ | ✓ | ✓ |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  | ✓ | ✓ | ✓ | ✓ |
| `media.aperture` |  | ✓ | ✓ | ✓ | ✓ |
| `media.aspectRatio` |  | ✓ | ✓ | ✓ | ✓ |
| `media.container` |  | ✓ | ✓ | ✓ | ✓ |
| `media.exposure` |  | ✓ | ✓ | ✓ | ✓ |
| `media.height` |  | ✓ | ✓ | ✓ | ✓ |
| `media.id` |  |  |  |  | ✓ |
| `media.iso` |  | ✓ | ✓ | ✓ | ✓ |
| `media.lens` |  | ✓ | ✓ | ✓ | ✓ |
| `media.make` |  | ✓ | ✓ | ✓ | ✓ |
| `media.model` |  | ✓ | ✓ | ✓ | ✓ |
| `media.width` |  | ✓ | ✓ | ✓ | ✓ |
| `media.parts.accessible` |  |  |  |  | ✓ |
| `media.parts.container` |  |  | ✓ | ✓ | ✓ |
| `media.parts.exists` |  |  |  |  | ✓ |
| `media.parts.file` |  |  | ✓ | ✓ | ✓ |
| `media.parts.id` |  |  |  |  | ✓ |
| `media.parts.key` |  |  |  |  | ✓ |
| `media.parts.size` |  |  | ✓ | ✓ | ✓ |
| `media.parts.sizeHuman` |  |  | ✓ | ✓ | ✓ |

</details>


### Clips

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `canNormalizeLoudness` |  |  |  | ✓ | ✓ |
| `chapterSource` |  |  |  | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `editionTitle` |  |  |  |  | ✓ |
| `episodeNumber` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentArt` |  |  |  | ✓ | ✓ |
| `grandparentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentKey` |  |  |  | ✓ | ✓ |
| `grandparentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentTheme` |  |  |  | ✓ | ✓ |
| `grandparentThumb` |  |  |  | ✓ | ✓ |
| `grandparentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `hasCommercialMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `hasCreditsMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `hasIntroMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `hasPreviewThumbnails` |  |  |  | ✓ | ✓ |
| `hasVoiceActivity` |  |  |  | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  |  |  |  | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `parentYear` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `seasonEpisode` |  | ✓ | ✓ | ✓ | ✓ |
| `seasonNumber` |  | ✓ | ✓ | ✓ | ✓ |
| `slug` |  |  |  |  | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewOffset` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `chapters.end` |  |  |  | ✓ | ✓ |
| `chapters.id` |  |  |  |  | ✓ |
| `chapters.index` |  |  |  | ✓ | ✓ |
| `chapters.start` |  |  |  | ✓ | ✓ |
| `chapters.tag` |  |  |  | ✓ | ✓ |
| `chapters.thumb` |  |  |  | ✓ | ✓ |
| `collections.id` |  |  |  |  | ✓ |
| `collections.tag` |  |  | ✓ | ✓ | ✓ |
| `directors.id` |  |  |  |  | ✓ |
| `directors.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  |  |  | ✓ |
| `markers.end` |  |  | ✓ | ✓ | ✓ |
| `markers.final` |  |  | ✓ | ✓ | ✓ |
| `markers.first` |  |  | ✓ | ✓ | ✓ |
| `markers.id` |  |  |  |  | ✓ |
| `markers.start` |  |  | ✓ | ✓ | ✓ |
| `markers.type` |  |  | ✓ | ✓ | ✓ |
| `producers.id` |  |  |  |  | ✓ |
| `producers.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.id` |  |  |  |  | ✓ |
| `roles.role` |  |  | ✓ | ✓ | ✓ |
| `roles.tag` |  |  | ✓ | ✓ | ✓ |
| `roles.thumb` |  |  |  |  | ✓ |
| `writers.id` |  |  |  |  | ✓ |
| `writers.tag` |  |  | ✓ | ✓ | ✓ |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  | ✓ | ✓ | ✓ | ✓ |
| `media.aspectRatio` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioChannels` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioCodec` |  | ✓ | ✓ | ✓ | ✓ |
| `media.audioProfile` |  | ✓ | ✓ | ✓ | ✓ |
| `media.bitrate` |  | ✓ | ✓ | ✓ | ✓ |
| `media.container` |  | ✓ | ✓ | ✓ | ✓ |
| `media.duration` |  | ✓ | ✓ | ✓ | ✓ |
| `media.has64bitOffsets` |  |  |  |  | ✓ |
| `media.hasVoiceActivity` |  |  |  |  | ✓ |
| `media.hdr` |  | ✓ | ✓ | ✓ | ✓ |
| `media.height` |  | ✓ | ✓ | ✓ | ✓ |
| `media.id` |  |  |  |  | ✓ |
| `media.isOptimizedVersion` |  | ✓ | ✓ | ✓ | ✓ |
| `media.optimizedForStreaming` |  |  |  |  | ✓ |
| `media.proxyType` |  |  |  |  | ✓ |
| `media.target` |  |  |  |  | ✓ |
| `media.title` |  |  |  |  | ✓ |
| `media.videoCodec` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoFrameRate` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoProfile` |  | ✓ | ✓ | ✓ | ✓ |
| `media.videoResolution` |  | ✓ | ✓ | ✓ | ✓ |
| `media.width` |  | ✓ | ✓ | ✓ | ✓ |
| `media.parts.accessible` |  |  |  |  | ✓ |
| `media.parts.audioProfile` |  |  | ✓ | ✓ | ✓ |
| `media.parts.container` |  |  | ✓ | ✓ | ✓ |
| `media.parts.deepAnalysisVersion` |  |  | ✓ | ✓ | ✓ |
| `media.parts.duration` |  |  | ✓ | ✓ | ✓ |
| `media.parts.exists` |  |  |  |  | ✓ |
| `media.parts.file` |  |  | ✓ | ✓ | ✓ |
| `media.parts.has64bitOffsets` |  |  |  |  | ✓ |
| `media.parts.hasPreviewThumbnails` |  |  | ✓ | ✓ | ✓ |
| `media.parts.hasThumbnail` |  |  |  |  | ✓ |
| `media.parts.id` |  |  |  |  | ✓ |
| `media.parts.indexes` |  |  | ✓ | ✓ | ✓ |
| `media.parts.key` |  |  |  |  | ✓ |
| `media.parts.optimizedForStreaming` |  |  | ✓ | ✓ | ✓ |
| `media.parts.packetLength` |  |  |  |  | ✓ |
| `media.parts.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.size` |  |  | ✓ | ✓ | ✓ |
| `media.parts.sizeHuman` |  |  | ✓ | ✓ | ✓ |
| `media.parts.syncItemId` |  |  |  |  | ✓ |
| `media.parts.syncState` |  |  |  |  | ✓ |
| `media.parts.videoProfile` |  |  | ✓ | ✓ | ✓ |
| `media.parts.audioStreams.audioChannelLayout` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitDepth` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitrate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.bitrateMode` |  |  |  |  | ✓ |
| `media.parts.audioStreams.canNormalizeLoudness` |  |  |  |  | ✓ |
| `media.parts.audioStreams.channels` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.duration` |  |  |  |  | ✓ |
| `media.parts.audioStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.gainOffset` |  |  |  |  | ✓ |
| `media.parts.audioStreams.id` |  |  |  |  | ✓ |
| `media.parts.audioStreams.index` |  |  |  |  | ✓ |
| `media.parts.audioStreams.key` |  |  |  |  | ✓ |
| `media.parts.audioStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.audioStreams.loudness` |  |  |  |  | ✓ |
| `media.parts.audioStreams.loudnessAnalysisVersion` |  |  |  |  | ✓ |
| `media.parts.audioStreams.lra` |  |  |  |  | ✓ |
| `media.parts.audioStreams.peak` |  |  |  |  | ✓ |
| `media.parts.audioStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.threshold` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
| `media.parts.audioStreams.visualImpaired` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.canAutoSync` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.container` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.forced` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.format` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.headerCompression` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.hearingImpaired` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.id` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.index` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.key` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.perfectMatch` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.providerTitle` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.score` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.selected` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.sourceKey` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.transient` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.type` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.userID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIBLCompatID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIBLPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIELPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVILevel` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIProfile` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIRPUPresent` |  |  |  |  | ✓ |
| `media.parts.videoStreams.DOVIVersion` |  |  |  |  | ✓ |
| `media.parts.videoStreams.anamorphic` |  |  |  |  | ✓ |
| `media.parts.videoStreams.bitDepth` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.bitrate` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.cabac` |  |  |  |  | ✓ |
| `media.parts.videoStreams.chromaLocation` |  |  |  |  | ✓ |
| `media.parts.videoStreams.chromaSubsampling` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.codecID` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codedHeight` |  |  |  |  | ✓ |
| `media.parts.videoStreams.codedWidth` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorPrimaries` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorRange` |  |  |  |  | ✓ |
| `media.parts.videoStreams.colorSpace` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.colorTrc` |  |  |  |  | ✓ |
| `media.parts.videoStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.duration` |  |  |  |  | ✓ |
| `media.parts.videoStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.frameRate` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.frameRateMode` |  |  |  |  | ✓ |
| `media.parts.videoStreams.hasScalingMatrix` |  |  |  |  | ✓ |
| `media.parts.videoStreams.hdr` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.height` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.id` |  |  |  |  | ✓ |
| `media.parts.videoStreams.index` |  |  |  |  | ✓ |
| `media.parts.videoStreams.key` |  |  |  |  | ✓ |
| `media.parts.videoStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.languageTag` |  |  |  |  | ✓ |
| `media.parts.videoStreams.level` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.pixelAspectRatio` |  |  |  |  | ✓ |
| `media.parts.videoStreams.pixelFormat` |  |  |  |  | ✓ |
| `media.parts.videoStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.refFrames` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.videoStreams.scanType` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.selected` |  |  |  |  | ✓ |
| `media.parts.videoStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.videoStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.videoStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.videoStreams.type` |  |  |  |  | ✓ |
| `media.parts.videoStreams.width` |  |  |  | ✓ | ✓ |

</details>


### Collections

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `childCount` |  | ✓ | ✓ | ✓ | ✓ |
| `collectionFilterBasedOnUser` |  |  |  |  | ✓ |
| `collectionMode` |  | ✓ | ✓ | ✓ | ✓ |
| `collectionSort` |  | ✓ | ✓ | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastRatedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `maxYear` |  | ✓ | ✓ | ✓ | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `minYear` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `subtype` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `theme` |  |  |  |  | ✓ |
| `themeFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `themeProvider` |  |  |  |  | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  | ✓ | ✓ | ✓ |
| `items` |  | ✓<br>Includes [Items](#collection-item) Level 1 | ✓<br>Includes [Items](#collection-item) Level 2 | ✓<br>Includes [Items](#collection-item) Level 3 | ✓<br>Includes [Items](#collection-item) Level 9 |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `items` |  | ✓<br>Includes [Items](#collection-item) Level 1 | ✓<br>Includes [Items](#collection-item) Level 2 | ✓<br>Includes [Items](#collection-item) Level 3 | ✓<br>Includes [Items](#collection-item) Level 9 |

</details>

* <a id="collection-item">**Note:**</a> Collection `items` can be [Movies](#movies), [Shows](#shows), [Seasons](#seasons), [Episodes](#episodes), [Artists](#artists), [Albums](#albums), or [Tracks](#tracks) depending on the type of collection.


### Playlists

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  |  | ✓ |
| `artFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `artProvider` |  |  |  |  | ✓ |
| `composite` |  |  |  | ✓ | ✓ |
| `content` |  |  |  |  | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `icon` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `logo` |  |  |  |  | ✓ |
| `logoFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `logoProvider` |  |  |  |  | ✓ |
| `metadataDirectory` |  |  |  |  | ✓ |
| `playlistType` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `smart` |  | ✓ | ✓ | ✓ | ✓ |
| `sourceURI` |  |  |  |  | ✓ |
| `squareArt` |  |  |  |  | ✓ |
| `squareArtFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `squareArtProvider` |  |  |  |  | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Resource Exports](#resource-exports) |  |  |  |  |
| `thumbProvider` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `items` |  | ✓<br>Includes [Items](#playlist-item) Level 1 | ✓<br>Includes [Items](#playlist-item) Level 2 | ✓<br>Includes [Items](#playlist-item) Level 3 | ✓<br>Includes [Items](#playlist-item) Level 9 |

</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `items` |  | ✓<br>Includes [Items](#playlist-item) Level 1 | ✓<br>Includes [Items](#playlist-item) Level 2 | ✓<br>Includes [Items](#playlist-item) Level 3 | ✓<br>Includes [Items](#playlist-item) Level 9 |

</details>

* <a id="playlist-item">**Note:**</a> Playlist `items` can be [Movies](#movies), [Episodes](#episodes), [Tracks](#tracks), or [Photos](#photos) depending on the type of playlist.
