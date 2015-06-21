#PlexPy

NB: This project is still very early in development.

This project is based on code from Headphones (https://github.com/rembo10/headphones) and PlexWatchWeb (https://github.com/ecleese/plexWatchWeb).

A python based web front-end for plexWatch.

* plexWatch Plex forum thread: http://forums.plexapp.com/index.php/topic/72552-plexwatch-plex-notify-script-send-push-alerts-on-new-sessions-and-stopped/
* plexWatch (Windows branch) Plex forum thread: http://forums.plexapp.com/index.php/topic/79616-plexwatch-windows-branch/


###Support
-----------
* PlexPy Wiki: https://github.com/drzoidberg33/plexpy/wiki


###Features
-----------
* Responsive web design viewable on desktop, tablet and mobile web browsers

* Themed to complement Plex/Web

* Easy configuration setup via html form

* Current Plex Media Server viewing activity including:
	* number of current users
	* title
	* progress
	* platform
	* user
	* state (playing, paused, buffering, etc)
	* stream type (direct, transcoded)
	* video type & resolution
	* audio type & channel count.

* Recently added media and how long ago it was added

* Global watching history with search/filtering & dynamic column sorting
	* date
	* user
	* platform
	* ip address (if enabled in plexWatch)
	* title
	* stream information details
	* start time
	* paused duration length
	* stop time
	* duration length
	* percentage completed

* full user list with general information and comparison stats 

* individual user information
	- username and gravatar (if available)
	- daily, weekly, monthly, all time stats for play count and duration length
	- individual platform stats for each user
	- public ip address history with last seen date and geo tag location
	- recently watched content
	- watching history

* charts **NOT YET IMPLEMENTED**
	- top 10 all time viewed content
	- top 10 viewed movies
	- top 10 viewed tv shows
	- top 10 viewed tv episodes

* content information pages **PARTIALLY IMPLEMENTED**
	- movies (includes watching history)
	- tv shows (includes top 10 watched episodes)
	- tv seasons
	- tv episodes (includes watching history)

## Installation and Notes

* [Installation page](../../wiki/Installation) shows you how to install PlexPy.
* [Usage guide](../../wiki/Usage-guide) introduces you to PlexPy.
* [Troubleshooting page](../../wiki/TroubleShooting) in the wiki can help you with common problems.

**Issues** can be reported on the GitHub issue tracker considering these rules:

1. Analyze your log, you just might find the solution yourself!
2. You read the wiki and searched existing issues, but this is not solving your problem.
3. Post the issue with a clear title, description and the HP log and use [proper markdown syntax](https://help.github.com/articles/github-flavored-markdown) to structure your text (code/log in code blocks). 
4. Close your issue when it's solved! If you found the solution yourself please comment so that others benefit from it.

**Feature requests** can be reported on the GitHub issue tracker too:

1. Search for similar existing 'issues', feature requests can be recognized by the label 'Request'.
2. If a similar Request exists, post a comment (+1, or add a new idea to the existing request), otherwise you can create a new one.

If you **comply with these rules** you can [post your request/issue](http://github.com/drzoidberg33/plexpy/issues).

**Support** the project by implementing new features, solving support tickets and provide bug fixes.

## License
This is free software under the GPL v3 open source license. Feel free to do with it what you wish, but any modification must be open sourced. A copy of the license is included.
