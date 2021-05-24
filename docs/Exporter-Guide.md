### Contents:

* [Introduction](#introduction)
* [File Formats](#file-format)
  * [Export Individual Files](#individual-files)
* [Metadata and Media Info Exports](#metadata-media-info-export)
  * [Metadata and Media Info Export Levels](#metadata-media-info-export-level)
  * [Custom Fields](#custom-field)
* [Image Exports](#image-export)
  * [Image Export Levels](#image-export-level)
* [Media Type Fields](#media-type-field)
  * [Movies](#movie)
  * [Shows](#show)
  * [Seasons](#season)
  * [Episodes](#episode)
  * [Artists](#artist)
  * [Albums](#album)
  * [Tracks](#track)
  * [Photo Albums](#photoalbum)
  * [Photos](#photo)
  * [Clips](#clip)
  * [Collections](#collection)
  * [Playlists](#playlist)

---

## <a id="introduction">Introduction</a>

The exporter feature of Tautulli allows you to export metadata and media info from your Plex library. The exporter can be accessed from various locations:

1. On any library page from the [Collections](./images/exporter_library_collections.png), [Playlists](./images/exporter_library_playlists.png), or [Export](./images/exporter_library_export.png) tabs. This will allow you to export all of your collections, playlists or all items for any library on your Plex server.
1. On any user page from the [Playlists](./images/exporter_user_playlists.png) tab. This will allow you to export all of a user's playlists for any user on your Plex server.
1. On any media info page from the [Export](./images/exporter_media_info.png) tab. This will allow you to export the metadata for any single media item on your Plex server.

Clicking on the export button on any of those pages will open up the [export metadata modal](./images/exporter_modal.png) where you can customize your export. All the customization options are described in the sections below.

The [metadata exports table](./images/exporter_table.png) on the library, user, or media info page will list all your previous exports and allow you to view or download a copy of the exported files. The download will return the exported file if only a single data file is exported, otherwise the download will return a `zip` archive containing all the exported data files and images. A progress percentage will be shown in the downloads column while an export is in progress. Exports are processed in the background so you may leave the page and check back later when it is complete.

* **Note:** The exporter only exports metadata. There is no import feature available in Tautulli.


## <a id="file-format">File Formats</a>

Metadata can be exported to various file formats. Notes about each file format is listed in the following table.

| File Format | Description |
| :---: | --- |
| `csv` | Export a comma-separated values file.<ul><li>**Note:** Each row in the `csv` file is unique so there may be multiple rows for the same media item (e.g. each `genres.tag` will be on it's own row so a single movie may have multiple rows).</li></ul> |
| `json` | Export a `json` format file.</li></ul> |
| `xml` | Export a `xml` format file.<ul><li>**Note:** The `xml` export is not the same as the [Plex XML data](https://support.plex.tv/articles/201998867-investigate-media-information-and-formats/).</li></ul> |
| `m3u8` | Only export a `m3u8` playlist file with the paths to all the media items without any additional metadata.<ul><li>**Note:** All files will be added to the playlist if there are multiple parts/versions.</li><li>**Note:** Export level selections are not allowed.</li></ul> |


### <a id="individual-files">Export Individual Files</a>

Enable this option to export one file for each collection/playlist/library item instead of a single file containing all items.

* **Note:** This option is only available when exporting collections, playlists or all items from the library or user page.


## <a id="metadata-media-info-export">Metadata and Media Info Exports</a>

The exporter has several predefined export levels. The export levels are separated into _metadata levels_ which include fields about the metadata of the item (e.g. `title`, `year`, `summary`, etc.) and _media info levels_ which include fields about the media file (e.g. `media.videoResolution`, `media.audioCodec`, `media.hdr`, etc.). The metadata level and media info level can be different, and the same level *does not* need to be selected for both. Higher levels will include all the fields from the lower levels. The fields that will be exported for each level are listed in the [Media Type Fields](#media-type-field) sections below.


### <a id="metadata-media-info-export-level">Metadata and Media Info Export Levels</a>

| Matadata Export Level | Name | Description |
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
| **Level 3** | Advanced Media Info | Fields for specific streams inside a media file part such as <br>`media.parts.videoStream.refFrames`, `media.parts.audioStream.samplingRate`, `media.parts.subtitleStream.language`, etc. |
| **Level 9** | All Media Info | All media info will be exported. |


### <a id="custom-field">Custom Fields</a>

[Custom fields](./images/exporter_custom_fields.png) can be added *in addition* to any export level. All fields from the selected metadata or media info level *plus* the custom fields will be exported. Start typing in the custom field box to search for a specific field to add. Some fields will be disabled to indicate that it is already included in the selected export level. All the available fields are listed in the [Media Type Fields](#media-type-field) sections below.

* **Note:** Custom fields for child media types are prefixed with the media type and separated with periods (`.`). The periods also delineate the tree structure in the `json` or `xml` file.
  * e.g. The `seasons.episodes.title` field will export the episode title for all seasons and all episodes for a TV show.

* **Note:** For [Collections](#collection) and [Playlists](#playlist), the `items` prefix can be different media types depending on the context. Refer to the [Media Type Fields](#media-type-field) sections below for all the possible media types.
  * e.g. The `items.title` field will be the movie title in a movie collection or TV show titles in a TV show collection.


## <a id="image-export">Image Exports</a>

[Poster/cover images and background artwork](./images/exporter_images.png) can be exported along with the metadata. Images will be exported to a `.images` folder alongside the data file with the extension `.thumb.jpg` for posters/covers and `.art.jpg` for background artwork. When downloading an export from the [metadata exports table](./images/exporter_table.png), the images will be included in a `zip` archive with the data file.

* **Warning:** Exporting images may take a long time!

* **Note:** Images will only be exported by the selected image export level for the following supported media types:
  * Movies, shows, seasons, artists, albums, collections and collection items, playlist items
* **Note:** Additional images for _any_ media type can be exported by adding `thumbFile` for posters/covers and `artFile` for background artwork to the custom metadata fields. Adding the custom field will export _all_ images of that type regardless of the selected image export level.
  * e.g. Adding `episodes.thumbFile` to the custom metadata fields will export all episode thumbnails even though it is not included in the supported image export media types.

### <a id="image-export-level">Image Export Levels</a>

| Poser and Cover Image Export Level | Name | Description | 
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


## <a id="media-type-field">Media Type Fields</a>


### <a id="movie">Movies</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `chapterSource` |  |  |  | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `languageOverride` |  |  |  |  | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `originalTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `studio` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `tagline` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
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
| `media.parts.audioStreams.channels` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.duration` |  |  |  |  | ✓ |
| `media.parts.audioStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.id` |  |  |  |  | ✓ |
| `media.parts.audioStreams.index` |  |  |  |  | ✓ |
| `media.parts.audioStreams.key` |  |  |  |  | ✓ |
| `media.parts.audioStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.container` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.forced` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.format` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.headerCompression` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.id` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.index` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.key` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.selected` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.transient` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.type` |  |  |  |  | ✓ |
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


### <a id="show">Shows</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `autoDeletionItemPolicyUnwatchedLibrary` |  |  |  |  | ✓ |
| `autoDeletionItemPolicyWatchedLibrary` |  |  |  |  | ✓ |
| `banner` |  |  |  | ✓ | ✓ |
| `bannerFile` |  |  |  |  | ✓ |
| `childCount` |  | ✓ | ✓ | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `episodeSort` |  |  |  |  | ✓ |
| `flattenSeasons` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `languageOverride` |  |  |  |  | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `network` |  | ✓ | ✓ | ✓ | ✓ |
| `originalTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `showOrdering` |  |  |  |  | ✓ |
| `studio` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `tagline` |  | ✓ | ✓ | ✓ | ✓ |
| `theme` |  |  |  | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
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
| `seasons` |  | ✓<br>Includes [Seasons](#show-season) Level 1 | ✓<br>Includes [Seasons](#show-season) Level 2 | ✓<br>Includes [Seasons](#show-season) Level 3 | ✓<br>Includes [Seasons](#show-season) Level 9 |
</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  |  |  |  | ✓ |
| `seasons` |  | ✓<br>Includes [Seasons](#show-season) Level 1 | ✓<br>Includes [Seasons](#show-season) Level 2 | ✓<br>Includes [Seasons](#show-season) Level 3 | ✓<br>Includes [Seasons](#show-season) Level 9 |
</details>


### <a id="season">Seasons</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  |  |  |  | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentTheme` |  |  |  | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewedLeafCount` |  |  |  |  | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `episodes` |  | ✓<br>Includes [Episodes](#season-episode) Level 1 | ✓<br>Includes [Episodes](#season-episode) Level 2 | ✓<br>Includes [Episodes](#season-episode) Level 3 | ✓<br>Includes [Episodes](#season-episode) Level 9 |
</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `episodes` |  | ✓<br>Includes [Episodes](#season-episode) Level 1 | ✓<br>Includes [Episodes](#season-episode) Level 2 | ✓<br>Includes [Episodes](#season-episode) Level 3 | ✓<br>Includes [Episodes](#season-episode) Level 9 |
</details>


### <a id="episode">Episodes</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` |  |  |  |  | ✓ |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `chapterSource` |  |  |  | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentArt` |  |  |  | ✓ | ✓ |
| `grandparentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentKey` |  |  |  | ✓ | ✓ |
| `grandparentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentTheme` |  |  |  | ✓ | ✓ |
| `grandparentThumb` |  |  |  | ✓ | ✓ |
| `grandparentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `hasIntroMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  | ✓ | ✓ | ✓ | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` |  |  |  |  | ✓ |
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
| `directors.id` |  |  |  |  | ✓ |
| `directors.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `markers.end` |  |  | ✓ | ✓ | ✓ |
| `markers.start` |  |  | ✓ | ✓ | ✓ |
| `markers.type` |  |  | ✓ | ✓ | ✓ |
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
| `media.parts.audioStreams.channels` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.duration` |  |  |  |  | ✓ |
| `media.parts.audioStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.id` |  |  |  |  | ✓ |
| `media.parts.audioStreams.index` |  |  |  |  | ✓ |
| `media.parts.audioStreams.key` |  |  |  |  | ✓ |
| `media.parts.audioStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.container` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.forced` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.format` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.headerCompression` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.id` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.index` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.key` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.selected` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.transient` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.type` |  |  |  |  | ✓ |
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


### <a id="artist">Artists</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `albumSort` |  |  |  |  | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
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
| `moods.id` |  |  |  |  | ✓ |
| `moods.tag` |  |  | ✓ | ✓ | ✓ |
| `similar.id` |  |  |  |  | ✓ |
| `similar.tag` |  |  | ✓ | ✓ | ✓ |
| `styles.id` |  |  |  |  | ✓ |
| `styles.tag` |  |  | ✓ | ✓ | ✓ |
| `albums` |  | ✓<br>Includes [Albums](#artist-album) Level 1 | ✓<br>Includes [Albums](#artist-album) Level 2 | ✓<br>Includes [Albums](#artist-album) Level 3 | ✓<br>Includes [Albums](#artist-album) Level 9 |
</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `locations` |  |  |  |  | ✓ |
| `albums` |  | ✓<br>Includes [Albums](#artist-album) Level 1 | ✓<br>Includes [Albums](#artist-album) Level 2 | ✓<br>Includes [Albums](#artist-album) Level 3 | ✓<br>Includes [Albums](#artist-album) Level 9 |
</details>


### <a id="album">Albums</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `loudnessAnalysisVersion` |  |  |  |  | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `studio` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
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
| `genres.id` |  |  |  |  | ✓ |
| `genres.tag` |  |  | ✓ | ✓ | ✓ |
| `labels.id` |  |  |  |  | ✓ |
| `labels.tag` |  |  | ✓ | ✓ | ✓ |
| `moods.id` |  |  |  |  | ✓ |
| `moods.tag` |  |  | ✓ | ✓ | ✓ |
| `styles.id` |  |  |  |  | ✓ |
| `styles.tag` |  |  | ✓ | ✓ | ✓ |
| `tracks` |  | ✓<br>Includes [Tracks](#album-track) Level 1 | ✓<br>Includes [Tracks](#album-track) Level 2 | ✓<br>Includes [Tracks](#album-track) Level 3 | ✓<br>Includes [Tracks](#album-track) Level 9 |
</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `tracks` |  | ✓<br>Includes [Tracks](#album-track) Level 1 | ✓<br>Includes [Tracks](#album-track) Level 2 | ✓<br>Includes [Tracks](#album-track) Level 3 | ✓<br>Includes [Tracks](#album-track) Level 9 |
</details>


### <a id="track">Tracks</a>

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
| `grandparentThumb` |  |  |  | ✓ | ✓ |
| `grandparentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `originalTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  | ✓ | ✓ | ✓ | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingCount` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `viewCount` |  |  |  | ✓ | ✓ |
| `viewOffset` |  |  |  |  | ✓ |
| `year` |  | ✓ | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
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
| `media.parts.audioStreams.loudness` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.lra` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.peak` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.profile` |  |  |  |  | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.startRamp` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
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
| `media.parts.lyricStreams.minLines` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.provider` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.selected` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.lyricStreams.timed` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.lyricStreams.type` |  |  |  |  | ✓ |
</details>


### <a id="photoalbum">Photo Albums</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `composite` |  |  |  |  | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
| `userRating` |  | ✓ | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `photoalbums` |  | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 1 | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 2 | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 3 | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 9 |
| `photos` |  | ✓<br>Includes [Photos](#photoalbum-photo) Level 1 | ✓<br>Includes [Photos](#photoalbum-photo) Level 2 | ✓<br>Includes [Photos](#photoalbum-photo) Level 3 | ✓<br>Includes [Photos](#photoalbum-photo) Level 9 |
| `clips` |  | ✓<br>Includes [Clips](#photoalbum-clip) Level 1 | ✓<br>Includes [Clips](#photoalbum-clip) Level 2 | ✓<br>Includes [Clips](#photoalbum-clip) Level 3 | ✓<br>Includes [Clips](#photoalbum-clip) Level 9 |
</details>

<details>
<summary><strong>Media Info Fields</strong></summary><br>

| Media Info Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `photoalbums` |  | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 1 | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 2 | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 3 | ✓<br>Includes [Photo Albums](#photoalbum-photoalbum) Level 9 |
| `photos` |  | ✓<br>Includes [Photos](#photoalbum-photo) Level 1 | ✓<br>Includes [Photos](#photoalbum-photo) Level 2 | ✓<br>Includes [Photos](#photoalbum-photo) Level 3 | ✓<br>Includes [Photos](#photoalbum-photo) Level 9 |
| `clips` |  | ✓<br>Includes [Clips](#photoalbum-clip) Level 1 | ✓<br>Includes [Clips](#photoalbum-clip) Level 2 | ✓<br>Includes [Clips](#photoalbum-clip) Level 3 | ✓<br>Includes [Clips](#photoalbum-clip) Level 9 |
</details>


### <a id="photo">Photos</a>

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
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
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


### <a id="clip">Clips</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` |  |  |  |  | ✓ |
| `audienceRating` |  | ✓ | ✓ | ✓ | ✓ |
| `audienceRatingImage` |  | ✓ | ✓ | ✓ | ✓ |
| `chapterSource` |  |  |  | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentArt` |  |  |  | ✓ | ✓ |
| `grandparentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentKey` |  |  |  | ✓ | ✓ |
| `grandparentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `grandparentTheme` |  |  |  | ✓ | ✓ |
| `grandparentThumb` |  |  |  | ✓ | ✓ |
| `grandparentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `hasIntroMarker` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `lastViewedAt` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `originallyAvailableAt` |  | ✓ | ✓ | ✓ | ✓ |
| `parentGuid` |  | ✓ | ✓ | ✓ | ✓ |
| `parentIndex` |  | ✓ | ✓ | ✓ | ✓ |
| `parentKey` |  |  |  | ✓ | ✓ |
| `parentRatingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `parentThumb` |  |  |  | ✓ | ✓ |
| `parentTitle` |  | ✓ | ✓ | ✓ | ✓ |
| `rating` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` |  |  |  |  | ✓ |
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
| `directors.id` |  |  |  |  | ✓ |
| `directors.tag` |  |  | ✓ | ✓ | ✓ |
| `fields.locked` |  |  | ✓ | ✓ | ✓ |
| `fields.name` |  |  | ✓ | ✓ | ✓ |
| `guids.id` |  |  | ✓ | ✓ | ✓ |
| `markers.end` |  |  | ✓ | ✓ | ✓ |
| `markers.start` |  |  | ✓ | ✓ | ✓ |
| `markers.type` |  |  | ✓ | ✓ | ✓ |
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
| `media.parts.audioStreams.channels` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.duration` |  |  |  |  | ✓ |
| `media.parts.audioStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.id` |  |  |  |  | ✓ |
| `media.parts.audioStreams.index` |  |  |  |  | ✓ |
| `media.parts.audioStreams.key` |  |  |  |  | ✓ |
| `media.parts.audioStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.profile` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.audioStreams.samplingRate` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.selected` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamIdentifier` |  |  |  |  | ✓ |
| `media.parts.audioStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.audioStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.audioStreams.type` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.codec` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.container` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.default` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.displayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.extendedDisplayTitle` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.forced` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.format` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.headerCompression` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.id` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.index` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.key` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.language` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.languageCode` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.requiredBandwidths` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.selected` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.streamType` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.title` |  |  |  | ✓ | ✓ |
| `media.parts.subtitleStreams.transient` |  |  |  |  | ✓ |
| `media.parts.subtitleStreams.type` |  |  |  |  | ✓ |
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


### <a id="collection">Collections</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `art` |  |  |  | ✓ | ✓ |
| `artBlurHash` |  |  |  |  | ✓ |
| `artFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `childCount` |  | ✓ | ✓ | ✓ | ✓ |
| `collectionMode` |  | ✓ | ✓ | ✓ | ✓ |
| `collectionSort` |  | ✓ | ✓ | ✓ | ✓ |
| `contentRating` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `index` |  |  |  |  | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `librarySectionID` |  |  |  |  | ✓ |
| `librarySectionKey` |  |  |  |  | ✓ |
| `librarySectionTitle` |  |  |  |  | ✓ |
| `maxYear` |  | ✓ | ✓ | ✓ | ✓ |
| `minYear` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `subtype` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
| `thumb` |  |  |  | ✓ | ✓ |
| `thumbBlurHash` |  |  |  |  | ✓ |
| `thumbFile` | Refer to [Image Exports](#image-export) |  |  |  |  |
| `title` |  | ✓ | ✓ | ✓ | ✓ |
| `titleSort` |  | ✓ | ✓ | ✓ | ✓ |
| `type` |  | ✓ | ✓ | ✓ | ✓ |
| `updatedAt` |  |  |  | ✓ | ✓ |
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

* <a id="collection-item">**Note:**</a> Collection `items` can be [Movies](#movie) or [Shows](#show) depending on the collection.


### <a id="playlist">Playlists</a>

<details>
<summary><strong>Metadata Fields</strong></summary><br>

| Metadata Field | Level 0 | Level 1 | Level 2 | Level 3 | Level 9 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `addedAt` |  | ✓ | ✓ | ✓ | ✓ |
| `composite` |  |  |  | ✓ | ✓ |
| `duration` |  | ✓ | ✓ | ✓ | ✓ |
| `durationHuman` |  | ✓ | ✓ | ✓ | ✓ |
| `guid` |  | ✓ | ✓ | ✓ | ✓ |
| `key` |  |  |  | ✓ | ✓ |
| `leafCount` |  |  |  |  | ✓ |
| `playlistType` |  | ✓ | ✓ | ✓ | ✓ |
| `ratingKey` |  | ✓ | ✓ | ✓ | ✓ |
| `smart` |  | ✓ | ✓ | ✓ | ✓ |
| `summary` |  | ✓ | ✓ | ✓ | ✓ |
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

* <a id="playlist-item">**Note:**</a> Playlist `items` can be [Movies](#movie), [Episodes](#episode), [Tracks](#track), or [Photos](#photo) depending on the playlist.
