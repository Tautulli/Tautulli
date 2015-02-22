# API Reference
The API is still pretty new and needs some serious cleaning up on the backend but should be reasonably functional. There are no error codes yet.

## General structure
The API endpoint is `http://ip:port + HTTP_ROOT + /api?apikey=$apikey&cmd=$command`

Data response in JSON formatted.

## API methods

### getLogs
Not working yet

### getVersion
Returns some version information: git_path, install_type, current_version, installed_version, commits_behind

### checkGithub
Updates the version information above and returns getVersion data

### shutdown
Shut down plexpy

### restart
Restart plexpy

### update
Update plexpy - you may want to check the install type in get version and not allow this if type==exe
