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

### getLogs
Possible params: sort='', search='', order='desc', regex='', start=0, end=0
Returns the plexpy log

### getApikey
Possible params: username='', password='' (required if auth is enabled)
Returns the apikey

### getSettings
No params
Returns the config file

### getVersion
No params
Returns some version information: git_path, install_type, current_version, installed_version, commits_behind

### getHistory
possible params: user=None, user_id=None, ,rating_key='', parent_rating_key='', grandparent_rating_key='', start_date=''
Returns

### getMetadata
Required params: rating_key
Returns metadata about a file

### getSync
Possible params: machine_id=None, user_id=None,
Returns

### getUserips
Possible params: user_id=None, user=None

### getPlayby
Possible params: time_range=30, y_axis='plays', playtype='total_plays_per_month'

### checkGithub
Updates the version information above and returns getVersion data

### shutdown
No params
Shut down plexpy

### restart
No params
Restart plexpy

### update
No params
Update plexpy - you may want to check the install type in get version and not allow this if type==exe
