# API Reference

The API is still pretty new and needs some serious cleaning up on the backend but should be reasonably functional. There are no error codes yet.

## General structure
The API endpoint is `http://ip:port + HTTP_ROOT + /api?apikey=$apikey&cmd=$command`

Response example
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

General parameters:
    out_type: 'xml',
    callback: 'pong',
    'debug': 1

## API methods

### backupdb
Makes a backup of the db, removes all but the 3 last backups

Args:
    cleanup: (bool, optional)


### delete_all_library_history


### delete_datatable_media_info_cache


### delete_library


### discover
Gets all your servers that are published to plextv

Returns:
    json:
        ```
        [{"httpsRequired": "0",
          "ip": "10.0.0.97",
          "value": "10.0.0.97",
          "label": "dude-PC",
          "clientIdentifier": "1234",
          "local": "1", "port": "32400"},
          {"httpsRequired": "0",
          "ip": "85.167.100.100",
          "value": "85.167.100.100",
          "label": "dude-PC",
          "clientIdentifier": "1234",
          "local": "0",
          "port": "10294"}
        ]
        ```


### docs
Returns a dict where commands are keys, docstring are value. 


### docs_md
Return a API.md to simplify api docs because of the decorator. 


### edit_library


### get_activity
Return processed and validated session list.

Returns:
    json:
        ```
        {stream_count: 1,
         session: [{dict}]
        }
        ```


### get_apikey
Fetches apikey

Args:
    username(string, optional): Your username
    password(string, optional): Your password

Returns:
    string: Apikey, args are required if auth is enabled
            makes and saves the apikey it does not exist


### get_date_formats
Get the date and time formats used by plexpy


### get_friends_list
Gets the friends list of the server owner for plex.tv


### get_full_users_list
Get a list all users that has access to your server

Returns:
        json:
            ```
            [{"username": "Hellowlol", "user_id": "1345",
              "thumb": "https://plex.tv/users/123aa/avatar",
              "is_allow_sync": null,
              "is_restricted": "0",
              "is_home_user": "0",
              "email": "John.Doe@email.com"}]
            ```


### get_library_list


### get_library_media_info


### get_library_sections
Get the library sections from pms

Returns:
        json:
            ```
            [{"section_id": 1, "section_name": "Movies"},
             {"section_id": 7, "section_name": "Music"},
             {"section_id": 2, "section_name": "TV Shows"}
            ]
            ```


### get_logs
Returns the log

Args:
    sort(string, optional): time, thread, msg, loglevel
    search(string, optional): 'string'
    order(string, optional): desc, asc
    regex(string, optional): 'regexstring'
    start(int, optional): int
    end(int, optional): int


Returns:
         ```{"response":
               {"msg": "Hey",
               "result": "success"},
               "data": [
                    {"time": "29-sept.2015",
                    "thread: "MainThread",
                    "msg: "Called x from y",
                    "loglevel": "DEBUG"
                    }
                ]
            }
        ```


### get_media_info_file_sizes


### get_metadata


### get_new_rating_keys
Grap the new rating keys

Args:
    rating_key(string): '',
    media_type(string): ''

Returns:
        json: ''


### get_old_rating_keys
Grap the old rating keys
Args:
    rating_key(string): '',
    media_type(string): ''
Returns:
        json: ''


### get_plays_by_date


### get_plays_by_dayofweek


### get_plays_by_hourofday


### get_plays_by_source_resolution


### get_plays_by_stream_resolution


### get_plays_by_stream_type


### get_plays_by_top_10_platforms


### get_plays_by_top_10_users


### get_plays_per_month


### get_plex_log


### get_plexwatch_export_data


### get_recently_added
Get all items that where recelty added to plex

Args:
    count(string): Number of items

Returns:
    dict: of all added items


### get_server_friendly_name


### get_server_id


### get_server_list
Find all servers published on plextv


### get_server_pref
Return a specified server preference.

Args:
    pref(string): 'name of preference'

Returns:
    String: ''


### get_server_prefs


### get_servers
All servers

Returns:
        json:
            ```
            {"MediaContainer": {"@size": "1", "Server":
                {"@name": "dude-PC",
                "@host": "10.0.0.97",
                "@address": "10.0.0.97",
                "@port": "32400",
                "@machineIdentifier": "1234",
                "@version": "0.9.15.2.1663-7efd046"}}}
            ```


### get_servers_info
Graps info about the server

Returns:
        json:
            ```
            [{"port": "32400",
              "host": "10.0.0.97",
              "version": "0.9.15.2.1663-7efd046",
              "name": "dude-PC",
              "machine_identifier": "1234"
              }
            ]
            ```


### get_sessions


### get_settings
Fetches all settings from the config file

Args:
    key(string, optional): 'Run the it without args to see all settings'

Returns:
        json:
            ```
            {General: {api_enabled: true, ...}
             Advanced: {cache_sizemb: "32", ...}}
            ```


### get_stream_type_by_top_10_platforms


### get_stream_type_by_top_10_users


### get_sync_item
Return sync item details.

Args:
    sync_id(string): unique sync id for item
    output_format(string, optional): 'xml/json'

Returns:
    List:
        ```
        {"data": [
                    {"username": "username",
                     "item_downloaded_percent_complete": 100,
                     "user_id": "134",
                     "failure": "",
                     "title": "Some Movie",
                     "total_size": "747195119",
                     "root_title": "Movies",
                     "music_bitrate": "128",
                     "photo_quality": "49",
                     "friendly_name": "username",
                     "device_name": "Username iPad",
                     "platform": "iOS",
                     "state": "complete",
                     "item_downloaded_count": "1",
                     "content_type": "video",
                     "metadata_type": "movie",
                     "video_quality": "49",
                     "item_count": "1",
                     "rating_key": "59207",
                     "item_complete_count": "1",
                     "sync_id": "1234"}
                ]
        }
        ```


### get_sync_lists


### get_sync_transcode_queue


### get_user_details
Get all details about a user from plextv


### get_user_list


### notify


### random_arnold_quotes


### refresh_libraries_list


### refresh_users_list
Refresh a users list in a own thread


### restart
Restarts plexpy 


### search


### sql
Query the db with raw sql, makes backup of
the db if the backup is older then 24h


### undelete_library


### update
Check for updates on Github 


### update_metadata_details


### update_section_ids

