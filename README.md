#PlexPy

[![Join the chat at https://gitter.im/drzoidberg33/plexpy](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/drzoidberg33/plexpy?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

A python based web application for monitoring, analytics and notifications for Plex Media Server (www.plex.tv).

This project is based on code from Headphones (https://github.com/rembo10/headphones) and PlexWatchWeb (https://github.com/ecleese/plexWatchWeb).

* plexPy forum thread: https://forums.plex.tv/discussion/169591/plexpy-another-plex-monitoring-program

If you'd like to buy me a beer, hit the donate button below. All donations go to the project maintainer (primarily for the procurement of liquid refreshment).

[![Donate](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=G9HZK9BDJLKT6)


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
	
* Top statistics on home page with configurable duration and measurement metric:
	* Most watched TV
	* Most popular TV
	* Most watched Movie
	* Most popular Movie
	* Most active user
	* Most active platform

* Recently added media and how long ago it was added

* Global watching history with search/filtering & dynamic column sorting
	* date
	* user
	* platform
	* ip address
	* title
	* stream information details
	* start time
	* paused duration length
	* stop time
	* duration length
	* watched progress
	* show/hide columns
	* delete mode - allows deletion of specific history items

* Full user list with general information and comparison stats 

* Individual user information
	* username and gravatar (if available)
	* daily, weekly, monthly, all time stats for play count and duration length
	* individual platform stats for each user
	* public ip address history with last seen date and geo tag location
	* recently watched content
	* watching history
	* synced items
	* assign users custom friendly names within PlexPy
	* assign users custom avatar URL within PlexPy
	* disable history logging per user
	* disable notifications per user
	* option to purge all history per user.

* Rich analytics presented using Highcharts graphing
	* user-selectable time periods of 30, 90 or 365 days
	* daily watch count and duration
	* totals by day of week and hours of the day
	* totals by top 10 platform
	* totals by top 10 users
	* detailed breakdown by transcode decision
	* source and stream resolutions
	* transcode decision counts by user and platform
	* total monthly counts
	
* Content information pages
	* movies (includes watching history)
	* tv shows (includes watching history)
	* tv seasons
	* tv episodes (includes watching history)

* Full sync list data on all users syncing items from your library

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

This software includes Highsoft software libraries which you may freely distribute for non-commercial use. Commerical users must licence this software, for more information visit https://shop.highsoft.com/faq/non-commercial#non-commercial-redistribution.