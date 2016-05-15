# API Reference

The API is still pretty new and needs some serious cleaning up on the backend but should be reasonably functional. There are no error codes yet.

## General structure
The API endpoint is `http://ip:port + HTTP_ROOT + /api/v2?apikey=$apikey&cmd=$command`

Response example (default `json`)
```
{
    "response": {
        "data": [
            {
                "loglevel": "INFO",
                "msg": "Signal 2 caught, saving and exiting...",
                "thread": "MainThread",
                "time": "22-sep-2015 01:42:56 "
            }
        ],
        "message": null,
        "result": "success"
    }
}
```
```
General optional parameters:

    out_type:   "json" or "xml"
    callback:   "pong"
    debug:      1
```

## API methods

### arnold
Get to the chopper!


### backup_config
Create a manual backup of the `config.ini` file. 


### backup_db
Create a manual backup of the `plexpy.db` file. 


### delete_all_library_history
Delete all PlexPy history for a specific library.

```
Required parameters:
    section_id (str):       The id of the Plex library section

Optional parameters:
    None

Returns:
    None
```


### delete_all_user_history
Delete all PlexPy history for a specific user.

```
Required parameters:
    user_id (str):          The id of the Plex user

Optional parameters:
    None

Returns:
    None
```


### delete_cache
Delete and recreate the cache directory.


### delete_datatable_media_info_cache
Delete the media info table cache for a specific library.

```
Required parameters:
    section_id (str):       The id of the Plex library section

Optional parameters:
    None

Returns:
    None
```


### delete_image_cache
Delete and recreate the image cache directory.


### delete_library
Delete a library section from PlexPy. Also erases all history for the library.

```
Required parameters:
    section_id (str):       The id of the Plex library section

Optional parameters:
    None

Returns:
    None
```


### delete_login_log
Delete the PlexPy login logs.

```
Required paramters:
    None

Optional parameters:
    None

Returns:
    None
```


### delete_notification_log
Delete the PlexPy notification logs.

```
Required paramters:
    None

Optional parameters:
    None

Returns:
    None
```


### delete_user
Delete a user from PlexPy. Also erases all history for the user.

```
Required parameters:
    user_id (str):          The id of the Plex user

Optional parameters:
    None

Returns:
    None
```


### docs
Return the api docs as a dict where commands are keys, docstring are value. 


### docs_md
Return the api docs formatted with markdown. 


### download_log
Download the PlexPy log file.


### edit_library
Update a library section on PlexPy.

```
Required parameters:
    section_id (str):           The id of the Plex library section

Optional parameters:
    custom_thumb (str):         The URL for the custom library thumbnail
    do_notify (int):            0 or 1
    do_notify_created (int):    0 or 1
    keep_history (int):         0 or 1

Returns:
    None
```


### edit_user
Update a user on PlexPy.

```
Required parameters:
    user_id (str):              The id of the Plex user

Optional paramters:
    friendly_name(str):         The friendly name of the user
    custom_thumb (str):         The URL for the custom user thumbnail
    do_notify (int):            0 or 1
    do_notify_created (int):    0 or 1
    keep_history (int):         0 or 1

Returns:
    None
```


### get_activity
Get the current activity on the PMS.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        {"stream_count": 3,
         "session":
            [{"art": "/library/metadata/1219/art/1462175063",
              "aspect_ratio": "1.78",
              "audio_channels": "6",
              "audio_codec": "ac3",
              "audio_decision": "transcode",
              "bif_thumb": "/library/parts/274169/indexes/sd/",
              "bitrate": "10617",
              "container": "mkv",
              "content_rating": "TV-MA",
              "duration": "2998290",
              "friendly_name": "Mother of Dragons",
              "grandparent_rating_key": "1219",
              "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
              "grandparent_title": "Game of Thrones",
              "height": "1078",
              "indexes": 1,
              "ip_address": "xxx.xxx.xxx.xxx",
              "labels": [],
              "machine_id": "83f189w617623ccs6a1lqpby",
              "media_index": "1",
              "media_type": "episode",
              "parent_media_index": "6",
              "parent_rating_key": "153036",
              "parent_thumb": "/library/metadata/153036/thumb/1462175062",
              "parent_title": "",
              "platform": "Chrome",
              "player": "Plex Web (Chrome)",
              "progress_percent": "0",
              "rating_key": "153037",
              "section_id": "2",
              "session_key": "291",
              "state": "playing",
              "throttled": "1",
              "thumb": "/library/metadata/153037/thumb/1462175060",
              "title": "The Red Woman",
              "transcode_audio_channels": "2",
              "transcode_audio_codec": "aac",
              "transcode_container": "mkv",
              "transcode_height": "1078",
              "transcode_key": "tiv5p524wcupe8nxegc26s9k9",
              "transcode_progress": 2,
              "transcode_protocol": "http",
              "transcode_speed": "0.0",
              "transcode_video_codec": "h264",
              "transcode_width": "1920",
              "user": "DanyKhaleesi69",
              "user_id": 8008135,
              "user_thumb": "https://plex.tv/users/568gwwoib5t98a3a/avatar",
              "video_codec": "h264",
              "video_decision": "copy",
              "video_framerate": "24p",
              "video_resolution": "1080",
              "view_offset": "",
              "width": "1920",
              "year": "2016"
              },
             {...},
             {...}
             ]
         }
```


### get_apikey
Get the apikey. Username and password are required
if auth is enabled. Makes and saves the apikey if it does not exist.

```
Required parameters:
    None

Optional parameters:
    username (str):     Your PlexPy username
    password (str):     Your PlexPy password

Returns:
    string:             "apikey"
```


### get_date_formats
Get the date and time formats used by PlexPy.

 ```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        {"date_format": "YYYY-MM-DD",
         "time_format": "HH:mm",
         }
```


### get_history
Get the PlexPy history.

```
Required parameters:
    None

Optional parameters:
    grouping (int):                 0 or 1
    user (str):                     "Jon Snow"
    user_id (int):                  133788
    rating_key (int):               4348
    parent_rating_key (int):        544
    grandparent_rating_key (int):   351
    start_date (str):               "YYYY-MM-DD"
    section_id (int):               2
    media_type (str):               "movie", "episode", "track"
    transcode_decision (str):       "direct play", "copy", "transcode",
    order_column (str):             "date", "friendly_name", "ip_address", "platform", "player",
                                    "full_title", "started", "paused_counter", "stopped", "duration"
    order_dir (str):                "desc" or "asc"
    start (int):                    Row to start from, 0
    length (int):                   Number of items to return, 25
    search (str):                   A string to search for, "Thrones"

Returns:
    json:
        {"draw": 1,
         "recordsTotal": 1000,
         "recordsFiltered": 250,
         "total_duration": "42 days 5 hrs 18 mins",
         "filter_duration": "10 hrs 12 mins",
         "data":
            [{"year": 2016,
              "paused_counter": 0,
              "player": "Plex Web (Chrome)",
              "parent_rating_key": 544,
              "parent_title": "",
              "duration": 263,
              "transcode_decision": "transcode",
              "rating_key": 4348,
              "user_id": 8008135,
              "thumb": "/library/metadata/4348/thumb/1462414561",
              "id": 1124,
              "platform": "Chrome",
              "media_type": "episode",
              "grandparent_rating_key": 351,
              "started": 1462688107,
              "full_title": "Game of Thrones - The Red Woman",
              "reference_id": 1123,
              "date": 1462687607,
              "percent_complete": 84,
              "ip_address": "xxx.xxx.xxx.xxx",
              "group_ids": "1124",
              "media_index": 17,
              "friendly_name": "Mother of Dragons",
              "watched_status": 0,
              "group_count": 1,
              "stopped": 1462688370,
              "parent_media_index": 7,
              "user": "DanyKhaleesi69"
              },
             {...},
             {...}
             ]
         }
```


### get_home_stats
Get the homepage watch statistics.

```
Required parameters:
    None

Optional parameters:
    grouping (int):         0 or 1
    time_range (str):       The time range to calculate statistics, '30'
    stats_type (int):       0 for plays, 1 for duration
    stats_count (str):      The number of top items to list, '5'

Returns:
    json:
        [{"stat_id": "top_movies",
          "stat_type": "total_plays",
          "rows": [{...}]
          },
         {"stat_id": "popular_movies",
          "rows": [{...}]
          },
         {"stat_id": "top_tv",
          "stat_type": "total_plays",
          "rows":
            [{"content_rating": "TV-MA",
              "friendly_name": "",
              "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
              "labels": [],
              "last_play": 1462380698,
              "media_type": "episode",
              "platform": "",
              "platform_type": "",
              "rating_key": 1219,
              "row_id": 1116,
              "section_id": 2,
              "thumb": "",
              "title": "Game of Thrones",
              "total_duration": 213302,
              "total_plays": 69,
              "user": "",
              "users_watched": ""
              },
             {...},
             {...}
             ]
          },
         {"stat_id": "popular_tv",
          "rows": [{...}]
          },
         {"stat_id": "top_music",
          "stat_type": "total_plays",
          "rows": [{...}]
          },
         {"stat_id": "popular_music",
          "rows": [{...}]
          },
         {"stat_id": "last_watched",
          "rows": [{...}]
          },
         {"stat_id": "top_users",
          "stat_type": "total_plays",
          "rows": [{...}]
          },
         {"stat_id": "top_platforms",
          "stat_type": "total_plays",
          "rows": [{...}]
          },
         {"stat_id": "most_concurrent",
          "rows": [{...}]
          }
         ]
```


### get_libraries
Get a list of all libraries on your server.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        [{"art": "/:/resources/show-fanart.jpg",
          "child_count": "3745",
          "count": "62",
          "parent_count": "240",
          "section_id": "2",
          "section_name": "TV Shows",
          "section_type": "show",
          "thumb": "/:/resources/show.png"
          },
         {...},
         {...}
         ]
```


### get_libraries_table
Get the data on the PlexPy libraries table.

```
Required parameters:
    None

Optional parameters:
    order_column (str):             "library_thumb", "section_name", "section_type", "count", "parent_count",
                                    "child_count", "last_accessed", "last_played", "plays", "duration"
    order_dir (str):                "desc" or "asc"
    start (int):                    Row to start from, 0
    length (int):                   Number of items to return, 25
    search (str):                   A string to search for, "Movies"

Returns:
    json:
        {"draw": 1,
         "recordsTotal": 10,
         "recordsFiltered": 10,
         "data":
            [{"child_count": 3745,
              "content_rating": "TV-MA",
              "count": 62,
              "do_notify": "Checked",
              "do_notify_created": "Checked",
              "duration": 1578037,
              "id": 1128,
              "keep_history": "Checked",
              "labels": [],
              "last_accessed": 1462693216,
              "last_played": "Game of Thrones - The Red Woman",
              "library_art": "/:/resources/show-fanart.jpg",
              "library_thumb": "",
              "media_index": 1,
              "media_type": "episode",
              "parent_count": 240,
              "parent_media_index": 6,
              "parent_title": "",
              "plays": 772,
              "rating_key": 153037,
              "section_id": 2,
              "section_name": "TV Shows",
              "section_type": "Show",
              "thumb": "/library/metadata/153036/thumb/1462175062",
              "year": 2016
              },
             {...},
             {...}
             ]
         }
```


### get_library_media_info
Get the data on the PlexPy media info tables.

```
Required parameters:
    section_id (str):               The id of the Plex library section, OR
    rating_key (str):               The grandparent or parent rating key

Optional parameters:
    section_type (str):             "movie", "show", "artist", "photo"
    order_column (str):             "added_at", "title", "container", "bitrate", "video_codec",
                                    "video_resolution", "video_framerate", "audio_codec", "audio_channels",
                                    "file_size", "last_played", "play_count"
    order_dir (str):                "desc" or "asc"
    start (int):                    Row to start from, 0
    length (int):                   Number of items to return, 25
    search (str):                   A string to search for, "Thrones"

Returns:
    json:
        {"draw": 1,
         "recordsTotal": 82,
         "recordsFiltered": 82,
         "filtered_file_size": 2616760056742,
         "total_file_size": 2616760056742,
         "data":
            [{"added_at": "1403553078",
              "audio_channels": "",
              "audio_codec": "",
              "bitrate": "",
              "container": "",
              "file_size": 253660175293,
              "grandparent_rating_key": "",
              "last_played": 1462380698,
              "media_index": "1",
              "media_type": "show",
              "parent_media_index": "",
              "parent_rating_key": "",
              "play_count": 15,
              "rating_key": "1219",
              "section_id": 2,
              "section_type": "show",
              "thumb": "/library/metadata/1219/thumb/1436265995",
              "title": "Game of Thrones",
              "video_codec": "",
              "video_framerate": "",
              "video_resolution": "",
              "year": "2011"
              },
             {...},
             {...}
             ]
         }
```


### get_library_names
Get a list of library sections and ids on the PMS.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        [{"section_id": 1, "section_name": "Movies"},
         {"section_id": 7, "section_name": "Music"},
         {"section_id": 2, "section_name": "TV Shows"},
         {...}
         ]
```


### get_logs
Get the PlexPy logs.

```
Required parameters:
    None

Optional parameters:
    sort (str):         "time", "thread", "msg", "loglevel"
    search (str):       A string to search for
    order (str):        "desc" or "asc"
    regex (str):        A regex string to search for
    start (int):        Row number to start from
    end (int):          Row number to end at

Returns:
    json:
        [{"loglevel": "DEBUG", 
          "msg": "Latest version is 2d10b0748c7fa2ee4cf59960c3d3fffc6aa9512b", 
          "thread": "MainThread", 
          "time": "2016-05-08 09:36:51 "
          }, 
         {...},
         {...}
         ]
```


### get_metadata
Get the metadata for a media item.

```
Required parameters:
    rating_key (str):       Rating key of the item
    media_info (bool):      True or False wheter to get media info

Optional parameters:
    None

Returns:
    json:
        {"metadata":
            {"actors": [
                "Kit Harington",
                "Emilia Clarke",
                "Isaac Hempstead-Wright",
                "Maisie Williams",
                "Liam Cunningham",
             ],
             "added_at": "1461572396",
             "art": "/library/metadata/1219/art/1462175063",
             "content_rating": "TV-MA",
             "directors": [
                "Jeremy Podeswa"
             ],
             "duration": "2998290",
             "genres": [
                "Adventure",
                "Drama",
                "Fantasy"
             ],
             "grandparent_rating_key": "1219",
             "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
             "grandparent_title": "Game of Thrones",
             "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
             "labels": [],
             "last_viewed_at": "1462165717",
             "library_name": "TV Shows",
             "media_index": "1",
             "media_type": "episode",
             "originally_available_at": "2016-04-24",
             "parent_media_index": "6",
             "parent_rating_key": "153036",
             "parent_thumb": "/library/metadata/153036/thumb/1462175062",
             "parent_title": "",
             "rating": "7.8",
             "rating_key": "153037",
             "section_id": "2",
             "studio": "HBO",
             "summary": "Jon Snow is dead. Daenerys meets a strong man. Cersei sees her daughter again.",
             "tagline": "",
             "thumb": "/library/metadata/153037/thumb/1462175060",
             "title": "The Red Woman",
             "updated_at": "1462175060",
             "writers": [
                "David Benioff",
                "D. B. Weiss"
             ],
             "year": "2016"
             }
         }
```


### get_new_rating_keys
Get a list of new rating keys for the PMS of all of the item's parent/children.

```
Required parameters:
    rating_key (str):       '12345'
    media_type (str):       "movie", "show", "season", "episode", "artist", "album", "track"

Optional parameters:
    None

Returns:
    json:
        {}
```


### get_notification_log
Get the data on the PlexPy notification logs table.

```
Required parameters:
    None

Optional parameters:
    order_column (str):             "timestamp", "agent_name", "notify_action",
                                    "subject_text", "body_text", "script_args"
    order_dir (str):                "desc" or "asc"
    start (int):                    Row to start from, 0
    length (int):                   Number of items to return, 25
    search (str):                   A string to search for, "Telegram"

Returns:
    json:
        {"draw": 1,
         "recordsTotal": 1039,
         "recordsFiltered": 163,
         "data":
            [{"agent_id": 13,
              "agent_name": "Telegram",
              "body_text": "Game of Thrones - S06E01 - The Red Woman [Transcode].",
              "id": 1000,
              "notify_action": "play",
              "poster_url": "http://i.imgur.com/ZSqS8Ri.jpg",
              "rating_key": 153037,
              "script_args": "[]",
              "session_key": 147,
              "subject_text": "PlexPy (Winterfell-Server)",
              "timestamp": 1462253821,
              "user": "DanyKhaleesi69",
              "user_id": 8008135
              },
             {...},
             {...}
             ]
         }
```


### get_old_rating_keys
Get a list of old rating keys from the PlexPy database for all of the item's parent/children.

```
Required parameters:
    rating_key (str):       '12345'
    media_type (str):       "movie", "show", "season", "episode", "artist", "album", "track"

Optional parameters:
    None

Returns:
    json:
        {}
```


### get_plays_by_date
Get graph data by date.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["YYYY-MM-DD", "YYYY-MM-DD", ...]
         "series":
            [{"name": "Movies", "data": [...]}
             {"name": "TV", "data": [...]},
             {"name": "Music", "data": [...]}
             ]
         }
```


### get_plays_by_dayofweek
Get graph data by day of the week.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["Sunday", "Monday", "Tuesday", ..., "Saturday"]
         "series":
            [{"name": "Movies", "data": [...]}
             {"name": "TV", "data": [...]},
             {"name": "Music", "data": [...]}
             ]
         }
```


### get_plays_by_hourofday
Get graph data by hour of the day.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["00", "01", "02", ..., "23"]
         "series":
            [{"name": "Movies", "data": [...]}
             {"name": "TV", "data": [...]},
             {"name": "Music", "data": [...]}
             ]
         }
```


### get_plays_by_source_resolution
Get graph data by source resolution.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["720", "1080", "sd", ...]
         "series":
            [{"name": "Direct Play", "data": [...]}
             {"name": "Direct Stream", "data": [...]},
             {"name": "Transcode", "data": [...]}
             ]
         }
```


### get_plays_by_stream_resolution
Get graph data by stream resolution.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["720", "1080", "sd", ...]
         "series":
            [{"name": "Direct Play", "data": [...]}
             {"name": "Direct Stream", "data": [...]},
             {"name": "Transcode", "data": [...]}
             ]
         }
```


### get_plays_by_stream_type
Get graph data by stream type by date.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["YYYY-MM-DD", "YYYY-MM-DD", ...]
         "series":
            [{"name": "Direct Play", "data": [...]}
             {"name": "Direct Stream", "data": [...]},
             {"name": "Transcode", "data": [...]}
             ]
         }
```


### get_plays_by_top_10_platforms
Get graph data by top 10 platforms.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["iOS", "Android", "Chrome", ...]
         "series":
            [{"name": "Movies", "data": [...]}
             {"name": "TV", "data": [...]},
             {"name": "Music", "data": [...]}
             ]
         }
```


### get_plays_by_top_10_users
Get graph data by top 10 users.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["Jon Snow", "DanyKhaleesi69", "A Girl", ...]
         "series":
            [{"name": "Movies", "data": [...]}
             {"name": "TV", "data": [...]},
             {"name": "Music", "data": [...]}
             ]
         }
```


### get_plays_per_month
Get graph data by month.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["Jan 2016", "Feb 2016", "Mar 2016", ...]
         "series":
            [{"name": "Movies", "data": [...]}
             {"name": "TV", "data": [...]},
             {"name": "Music", "data": [...]}
             ]
         }
```


### get_plex_log
Get the PMS logs.

```
Required parameters:
    None

Optional parameters:
    window (int):           The number of tail lines to return
    log_type (str):         "server" or "scanner"

Returns:
    json:
        [["May 08, 2016 09:35:37",
          "DEBUG",
          "Auth: Came in with a super-token, authorization succeeded."
          ],
         [...],
         [...]
         ]
```


### get_pms_token
Get the user's Plex token used for PlexPy.

```
Required parameters:
    username (str):     The Plex.tv username
    password (str):     The Plex.tv password

Optional parameters:
    None

Returns:
    string:             The Plex token used for PlexPy
```


### get_recently_added
Get all items that where recelty added to plex.

```
Required parameters:
    count (str):        Number of items to return

Optional parameters:
    section_id (str):   The id of the Plex library section

Returns:
    json:
        {"recently_added":
            [{"added_at": "1461572396",
              "grandparent_rating_key": "1219",
              "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
              "grandparent_title": "Game of Thrones",
              "library_name": "",
              "media_index": "1",
              "media_type": "episode",
              "parent_media_index": "6",
              "parent_rating_key": "153036",
              "parent_thumb": "/library/metadata/153036/thumb/1462175062",
              "parent_title": "",
              "rating_key": "153037",
              "section_id": "2",
              "thumb": "/library/metadata/153037/thumb/1462175060",
              "title": "The Red Woman",
              "year": "2016"
              },
             {...},
             {...}
             ]
         }
```


### get_server_friendly_name
Get the name of the PMS.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    string:     "Winterfell-Server"
```


### get_server_id
Get the PMS server identifier.

```
Required parameters:
    hostname (str):     'localhost' or '192.160.0.10'
    port (int):         32400

Optional parameters:
    ssl (int):          0 or 1
    remote (int):       0 or 1

Returns:
    string:             The unique PMS identifier
```


### get_server_identity
Get info about the local server.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        [{"machine_identifier": "ds48g4r354a8v9byrrtr697g3g79w",
          "version": "0.9.15.x.xxx-xxxxxxx"
          }
         ]
```


### get_server_list
Get all your servers that are published to Plex.tv.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        [{"clientIdentifier": "ds48g4r354a8v9byrrtr697g3g79w",
          "httpsRequired": "0",
          "ip": "xxx.xxx.xxx.xxx",
          "label": "Winterfell-Server",
          "local": "1",
          "port": "32400",
          "value": "xxx.xxx.xxx.xxx"
          },
         {...},
         {...}
         ]
```


### get_server_pref
Get a specified PMS server preference.

```
Required parameters:
    pref (str):         Name of preference

Returns:
    string:             Value of preference
```


### get_servers_info
Get info about the PMS.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        [{"port": "32400",
          "host": "10.0.0.97",
          "version": "0.9.15.2.1663-7efd046",
          "name": "Winterfell-Server",
          "machine_identifier": "ds48g4r354a8v9byrrtr697g3g79w"
          }
         ]
```


### get_settings
Gets all settings from the config file.

```
Required parameters:
    None

Optional parameters:
    key (str):      Name of a config section to return

Returns:
    json:
        {"General": {"api_enabled": true, ...}
         "Advanced": {"cache_sizemb": "32", ...},
         ...
         }
```


### get_stream_type_by_top_10_platforms
Get graph data by stream type by top 10 platforms.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["iOS", "Android", "Chrome", ...]
         "series":
            [{"name": "Direct Play", "data": [...]}
             {"name": "Direct Stream", "data": [...]},
             {"name": "Transcode", "data": [...]}
             ]
         }
```


### get_stream_type_by_top_10_users
Get graph data by stream type by top 10 users.

```
Required parameters:
    None

Optional parameters:
    time_range (str):       The number of days of data to return
    y_axis (str):           "plays" or "duration"
    user_id (str):          The user id to filter the data

Returns:
    json:
        {"categories":
            ["Jon Snow", "DanyKhaleesi69", "A Girl", ...]
         "series":
            [{"name": "Direct Play", "data": [...]}
             {"name": "Direct Stream", "data": [...]},
             {"name": "Transcode", "data": [...]}
            ]
         }
```


### get_synced_items
Get a list of synced items on the PMS.

```
Required parameters:
    machine_id (str):       The PMS identifier

Optional parameters:
    user_id (str):          The id of the Plex user

Returns:
    json:
        [{"content_type": "video",
          "device_name": "Tyrion's iPad",
          "failure": "",
          "friendly_name": "Tyrion Lannister",
          "item_complete_count": "0",
          "item_count": "1",
          "item_downloaded_count": "0",
          "item_downloaded_percent_complete": 0,
          "metadata_type": "movie",
          "music_bitrate": "192",
          "photo_quality": "74",
          "platform": "iOS",
          "rating_key": "154092",
          "root_title": "Deadpool",
          "state": "pending",
          "sync_id": "11617019",
          "title": "Deadpool",
          "total_size": "0",
          "user_id": "696969",
          "username": "DrukenDwarfMan",
          "video_quality": "60"
          },
         {...},
         {...}
         ]
```


### get_user_ips
Get the data on PlexPy users IP table.

```
Required parameters:
    user_id (str):                  The id of the Plex user

Optional parameters:
    order_column (str):             "last_seen", "ip_address", "platform", "player",
                                    "last_played", "play_count"
    order_dir (str):                "desc" or "asc"
    start (int):                    Row to start from, 0
    length (int):                   Number of items to return, 25
    search (str):                   A string to search for, "xxx.xxx.xxx.xxx"

Returns:
    json:
        {"draw": 1,
         "recordsTotal": 2344,
         "recordsFiltered": 10,
         "data":
            [{"friendly_name": "Jon Snow",
              "id": 1121,
              "ip_address": "xxx.xxx.xxx.xxx",
              "last_played": "Game of Thrones - The Red Woman",
              "last_seen": 1462591869,
              "media_index": 1,
              "media_type": "episode",
              "parent_media_index": 6,
              "parent_title": "",
              "platform": "Chrome",
              "play_count": 149,
              "player": "Plex Web (Chrome)",
              "rating_key": 153037,
              "thumb": "/library/metadata/153036/thumb/1462175062",
              "transcode_decision": "transcode",
              "user_id": 133788,
              "year": 2016
              },
             {...},
             {...}
             ]
         }
```


### get_user_logins
Get the data on PlexPy user login table. 

```
Required parameters:
    user_id (str):                  The id of the Plex user

Optional parameters:
    order_column (str):             "date", "time", "ip_address", "host", "os", "browser"
    order_dir (str):                "desc" or "asc"
    start (int):                    Row to start from, 0
    length (int):                   Number of items to return, 25
    search (str):                   A string to search for, "xxx.xxx.xxx.xxx"

Returns:
    json:
        {"draw": 1,
         "recordsTotal": 2344,
         "recordsFiltered": 10,
         "data":
            [{"browser": "Safari 7.0.3", 
              "friendly_name": "Jon Snow", 
              "host": "http://plexpy.castleblack.com", 
              "ip_address": "xxx.xxx.xxx.xxx", 
              "os": "Mac OS X", 
              "timestamp": 1462591869, 
              "user": "LordCommanderSnow", 
              "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A", 
              "user_group": "guest", 
              "user_id": 133788
              },
             {...},
             {...}
             ]
         }
```


### get_user_names
Get a list of all user and user ids.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        [{"friendly_name": "Jon Snow", "user_id": 133788},
         {"friendly_name": "DanyKhaleesi69", "user_id": 8008135},
         {"friendly_name": "Tyrion Lannister", "user_id": 696969},
         {...},
        ]
```


### get_users
Get a list of all users that have access to your server.

```
Required parameters:
    None

Optional parameters:
    None

Returns:
    json:
        [{"email": "Jon.Snow.1337@CastleBlack.com",
          "filter_all": "",
          "filter_movies": "",
          "filter_music": "",
          "filter_photos": "",
          "filter_tv": "",
          "is_allow_sync": null,
          "is_home_user": "1",
          "is_restricted": "0",
          "thumb": "https://plex.tv/users/k10w42309cynaopq/avatar",
          "user_id": "133788",
          "username": "Jon Snow"
          },
         {...},
         {...}
         ]
```


### get_users_table
Get the data on PlexPy users table.

```
Required parameters:
    None

Optional parameters:
    order_column (str):             "user_thumb", "friendly_name", "last_seen", "ip_address", "platform",
                                    "player", "last_played", "plays", "duration"
    order_dir (str):                "desc" or "asc"
    start (int):                    Row to start from, 0
    length (int):                   Number of items to return, 25
    search (str):                   A string to search for, "Jon Snow"

Returns:
    json:
        {"draw": 1,
         "recordsTotal": 10,
         "recordsFiltered": 10,
         "data":
            [{"allow_guest": "Checked",
              "do_notify": "Checked",
              "duration": 2998290,
              "friendly_name": "Jon Snow",
              "id": 1121,
              "ip_address": "xxx.xxx.xxx.xxx",
              "keep_history": "Checked",
              "last_played": "Game of Thrones - The Red Woman",
              "last_seen": 1462591869,
              "media_index": 1,
              "media_type": "episode",
              "parent_media_index": 6,
              "parent_title": "",
              "platform": "Chrome",
              "player": "Plex Web (Chrome)",
              "plays": 487,
              "rating_key": 153037,
              "thumb": "/library/metadata/153036/thumb/1462175062",
              "transcode_decision": "transcode",
              "user_id": 133788,
              "user_thumb": "https://plex.tv/users/568gwwoib5t98a3a/avatar",
              "year": 2016
              },
             {...},
             {...}
             ]
         }
```


### import_database
Import a PlexWatch or Plexivity database into PlexPy.

```
Required parameters:
    app (str):                      "plexwatch" or "plexivity"
    database_path (str):            The full path to the plexwatch database file
    table_name (str):               "processed" or "grouped"

Optional parameters:
    import_ignore_interval (int):   The minimum number of seconds for a stream to import

Returns:
    None
```


### notify
Send a notification using PlexPy.

```
Required parameters:
    agent_id(str):          The id of the notification agent to use
    subject(str):           The subject of the message
    body(str):              The body of the message

Optional parameters:
    None

Returns:
    None
```


### refresh_libraries_list
Refresh the PlexPy libraries list. 


### refresh_users_list
Refresh the PlexPy users list. 


### restart
Restart PlexPy. 


### search
Get search results from the PMS.

```
Required parameters:
    query (str):        The query string to search for

Returns:
    json:
        {"results_count": 69,
         "results_list":
            {"movie":
                [{...},
                 {...},
                 ]
             },
            {"episode":
                [{...},
                 {...},
                 ]
             },
            {...}
         }
```


### sql
Query the PlexPy database with raw SQL. Automatically makes a backup of
the database if the latest backup is older then 24h. `api_sql` must be
manually enabled in the config file.

```
Required parameters:
    query (str):        The SQL query

Optional parameters:
    None

Returns:
    None
```


### undelete_library
Restore a deleted library section to PlexPy.

```
Required parameters:
    section_id (str):       The id of the Plex library section
    section_name (str):     The name of the Plex library section

Optional parameters:
    None

Returns:
    None
```


### undelete_user
Restore a deleted user to PlexPy.

```
Required parameters:
    user_id (str):          The id of the Plex user
    username (str):         The username of the Plex user

Optional parameters:
    None

Returns:
    None
```


### update
Check for PlexPy updates on Github. 


### update_metadata_details
Update the metadata in the PlexPy database by matching rating keys.
Also updates all parents or children of the media item if it is a show/season/episode
or artist/album/track.

```
Required parameters:
    old_rating_key (str):       12345
    new_rating_key (str):       54321
    media_type (str):           "movie", "show", "season", "episode", "artist", "album", "track"

Optional parameters:
    None

Returns:
    None
```

