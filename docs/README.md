# Introduction

A python based web application for monitoring, analytics and notifications for [Plex Media Server](https://plex.tv).

This project is based on code from [Headphones](https://github.com/rembo10/headphones) and [PlexWatchWeb](https://github.com/ecleese/plexWatchWeb).

## Features

* Responsive web design viewable on desktop, tablet and mobile web browsers.
* Themed to complement Plex/Web.
* Easy configuration setup \(no separate web server required\).
* Monitor current Plex Media Server activity.
* Fully customizable notifications for stream activity and recently added media.
* Top statistics on home page with configurable duration and measurement metric.
* Global watching history with search/filtering & dynamic column sorting.
* Full user list with general information and comparison stats.
* Individual user information including devices IP addresses.
* Complete library statistics and media file information.
* Rich analytics presented using Highcharts graphing.
* Beautiful content information pages.
* Full sync list data on all users syncing items from your library.
* And many more!!

## Preview

[Full preview gallery available on our website](http://tautulli.com)

![Tautulli Homepage](https://tautulli.com/images/screenshots/activity-compressed.jpg?v=2)

## Installation

[![](https://img.shields.io/badge/python->=3.6-blue?style=flat-square)](https://python.org/downloads) [![](https://img.shields.io/docker/pulls/tautulli/tautulli?style=flat-square)](https://hub.docker.com/r/tautulli/tautulli) [![](https://img.shields.io/docker/stars/tautulli/tautulli?style=flat-square)](https://hub.docker.com/r/tautulli/tautulli) [![ Status \| Branch: \`master\` \| Branch: \`beta\` \| Branch: \`nightly\` ](https://img.shields.io/github/downloads/Tautulli/Tautulli/total?style=flat-square)](https://github.com/Tautulli/Tautulli/releases/latest)

\| --- \| --- \| --- \| --- \| \| Release \| [![](https://img.shields.io/github/v/release/Tautulli/Tautulli?style=flat-square)](https://github.com/Tautulli/Tautulli/releases/latest)   
 [![](https://img.shields.io/github/release-date/Tautulli/Tautulli?style=flat-square&color=blue)](https://github.com/Tautulli/Tautulli/releases/latest) \| [![](https://img.shields.io/github/v/release/Tautulli/Tautulli?include_prereleases&style=flat-square)](https://github.com/Tautulli/Tautulli/releases)   
 [![](https://img.shields.io/github/commits-since/Tautulli/Tautulli/latest/beta?style=flat-square&color=blue)](https://github.com/Tautulli/Tautulli/commits/beta) \| [![](https://img.shields.io/github/last-commit/Tautulli/Tautulli/nightly?style=flat-square&color=blue)](https://github.com/Tautulli/Tautulli/commits/nightly)   
 [![](https://img.shields.io/github/commits-since/Tautulli/Tautulli/latest/nightly?style=flat-square&color=blue)](https://github.com/Tautulli/Tautulli/commits/nightly) \| \| Docker \| [![](https://img.shields.io/badge/docker-latest-blue?style=flat-square)](https://hub.docker.com/r/tautulli/tautulli)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Docker/master?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Docker"+branch%3Amaster) \| [![](https://img.shields.io/badge/docker-beta-blue?style=flat-square)](https://hub.docker.com/r/tautulli/tautulli)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Docker/beta?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Docker"+branch%3Abeta) \| [![](https://img.shields.io/badge/docker-nightly-blue?style=flat-square)](https://hub.docker.com/r/tautulli/tautulli)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Docker/nightly?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Docker"+branch%3Anightly) \| \| Snap \| [![](https://img.shields.io/badge/snap-stable-blue?style=flat-square)](https://snapcraft.io/tautulli)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Snap/master?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Snap"+branch%3Amaster) \| [![](https://img.shields.io/badge/snap-beta-blue?style=flat-square)](https://snapcraft.io/tautulli)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Snap/beta?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Snap"+branch%3Abeta) \| [![](https://img.shields.io/badge/snap-edge-blue?style=flat-square)](https://snapcraft.io/tautulli)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Snap/nightly?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Snap"+branch%3Anightly) \| \| Installer \| [![](https://img.shields.io/github/v/release/Tautulli/Tautulli?label=windows&style=flat-square)](https://github.com/Tautulli/Tautulli/releases/latest)   
 [![](https://img.shields.io/github/v/release/Tautulli/Tautulli?label=macos&style=flat-square)](https://github.com/Tautulli/Tautulli/releases/latest)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Installers/master?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Installers"+branch%3Amaster) \| [![](https://img.shields.io/github/v/release/Tautulli/Tautulli?label=windows&include_prereleases&style=flat-square)](https://github.com/Tautulli/Tautulli/releases)   
 [![](https://img.shields.io/github/v/release/Tautulli/Tautulli?label=macos&include_prereleases&style=flat-square)](https://github.com/Tautulli/Tautulli/releases)   
 [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Installers/beta?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Installers"+branch%3Abeta) \| [![](https://img.shields.io/github/workflow/status/Tautulli/Tautulli/Publish%20Installers/nightly?style=flat-square)](https://github.com/Tautulli/Tautulli/actions?query=workflow%3A"Publish+Installers"+branch%3Anightly) \|

Read the [Installation Guides](https://github.com/Tautulli/Tautulli/wiki/Installation) for instructions on how to install Tautulli.

## Support

[![](https://img.shields.io/badge/github-wiki-black?style=flat-square)](https://github.com/Tautulli/Tautulli/wiki) [![](https://img.shields.io/discord/183396325142822912?label=discord&style=flat-square&color=7289DA)](https://tautulli.com/discord) [![](https://img.shields.io/reddit/subreddit-subscribers/tautulli?label=reddit&style=flat-square&color=FF5700)](https://reddit.com/r/Tautulli) [![](https://img.shields.io/badge/plex%20forums-discussion-E5A00D?style=flat-square)](https://forums.plex.tv/t/tautulli-monitor-your-plex-media-server/225242) [![](https://img.shields.io/badge/github-issues-black?style=flat-square)](https://github.com/Tautulli/Tautulli/issues)

If you think you've found a bug in Tautulli make sure you have read the [FAQ](https://github.com/Tautulli/Tautulli/wiki/Frequently-Asked-Questions) first to make sure it hasn't been covered by one of the questions there. If your problem isn't answered in the FAQ try the following first:

* Update to the latest version of Tautulli.
* Turning your device off and on again.
* Analyzing your logs, you just might find the solution yourself!
* Using the **search** function to see if this issue has already been reported/solved.
* Checking the [Wiki](https://github.com/Tautulli/Tautulli/wiki) for [Installation](https://github.com/Tautulli/Tautulli/wiki/Installation) instructions and reading the [FAQs](https://github.com/Tautulli/Tautulli/wiki/Frequently-Asked-Questions).
* For basic questions try asking on [Discord](https://tautulli.com/discord), [Reddit](https://reddit.com/r/Tautulli), 

  or the [Plex Forums](https://forums.plex.tv/t/tautulli-monitor-your-plex-media-server/225242) first before opening an issue.

### If nothing has worked:

1. Please check the [issues tracker](https://github.com/Tautulli/Tautulli/issues) to see if someone else has already reported the bug.
2. If this is a new bug, open a [bug report](https://github.com/Tautulli/Tautulli/issues/new/choose) on the issues tracker.
3. Provide a clear title to easily help identify your problem.
4. Use proper [Markdown syntax](https://help.github.com/articles/github-flavored-markdown) to structure your post \(i.e. code/log in code blocks\).
5. Make sure to fill out the required information on the issue template.
6. Close your issue when it's solved! If you found the solution yourself please

   comment so that others benefit from it.

## Feature Requests

1. Pleases check the [issues tracker](https://github.com/Tautulli/Tautulli/issues) to see if someone else has already requested the feature.

   If a similar idea has already been requested, _give it a thumbs up_. \*\*Do not comment

   with `+1` or something similar as it creates unnecessary spam.\*\*

2. If this is a new feature request, open a [feature request](https://github.com/Tautulli/Tautulli/issues/new/choose) on the issues tracker.

## License

[![](https://img.shields.io/github/license/Tautulli/Tautulli?style=flat-square)](https://github.com/Tautulli/Tautulli/blob/master/LICENSE)

This is free software under the GPL v3 open source license. Feel free to do with it what you wish, but any modification must be open sourced. A copy of the license is included.

This software includes Highsoft software libraries which you may freely distribute for non-commercial use. Commerical users must licence this software, for more information visit [https://shop.highsoft.com/faq/non-commercial\#non-commercial-redistribution](https://shop.highsoft.com/faq/non-commercial#non-commercial-redistribution).

