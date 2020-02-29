# Changelog

## v2.1.44 (2020-02-05)

* Monitoring:
  * Fix: SDR source video being identified as HDR stream video.
* Notifications:
  * Fix: Unable to select condition operator for video color parameters.
* UI:
  * Fix: Capitalization for platforms on history tables.


## v2.1.43 (2020-02-03)

* Monitoring:
  * New: Added HDR indicator on activity card.
  * New: Added dynamic range to history steam info modal.
* Notifications:
  * Fix: Webhook notification body sent as incorrect data type when Content-Type header is overridden.
  * Fix: Telegram notification character limit incorrect for unicode characters.
  * New: Added color and dynamic range notification parameters.
* Newsletters:
  * Fix: Episodes and Albums plural spelling on recently added newsletter section headers.
* UI:
  * Fix: Windows and macOS platform capitalization.
  * Fix: Season number 0 not shown for episodes on history tables.
* Other:
  * Change: Mask email addresses in logs.
  * Change: Update deprecated GitHub access token URL parameter to Authorization header.  


## v2.1.42 (2020-01-04)

* Other:
  * Fix: SSL certificate error when installing GeoLite2 database.
  * Change: Verify MaxMind license key and GeoLite2 database path before installing.
  * Change: Disable GeoLite2 database uninstall button when it is not installed.


## v2.1.41 (2019-12-30)

* Other:
  * Fix: Failing to extract the GeoLite2 database on Windows.


## v2.1.40 (2019-12-30)

* UI:
  * Change: Moved 3rd Party API settings to new tab in the settings.
* Graphs:
  * Change: Improve calculating month ranges for Play Totals graphs.
* Other:
  * Fix: Failing to verify a Plex Media Server using a hostname.
  * Change: A license key is now required to install the MaxMind GeoLite2 database for IP geolocation. Please follow the guide in the wiki to reinstall the GeoLite2 database.
  * Change: The GeoLite2 database will now automatically update periodically if installed.


## v2.1.39 (2019-12-08)

* UI:
  * New: Added creating admin username and password to setup wizard.
* API:
  * Change: Remove default notification subject and body for notify API command.
* Other:
  * Change: Check for database corruption when making backup.


## v2.1.38 (2019-11-17)

* Notifications:
  * New: Added custom JSON headers to the webhook notification agent.
* UI:
  * Fix: Homepage recently watched card not showing grouped history.
* Other:
  * New: Added GitHub sponsor donation option.
  * Change: Improve resolving hostnames.


## v2.1.37 (2019-10-11)

* Notifications:
  * Fix: Last.fm URLs linking to artist page instead of the album page.
  * New: Added option for MusicBrainz lookup for music notifications. Option must be enabled under 3rd Party APIs in the settings.
  * New: Added MusicBrainz ID and MusicBrainz URL notification parameters.
  * Change: Automatically truncate Discord description summary to 2048 characters.


## v2.1.36-beta (2019-10-05)

* Monitoring:
  * Fix: Activity card title not updating after pre-rolls or auto-play.
* History:
  * Fix: Display correct interlaced or progressive video scan type on stream data modal.
* Graphs:
  * New: Separate interlaced and progressive video scan type on source and stream resolution graphs.
* API:
  * New: Added parent_guid and grandparent_guid to get_activity and get_metadata commands.


## v2.1.35-beta (2019-09-24)

* Monitoring:
  * Fix: Audio shown as blank on activity cards when changing audio tracks during direct play.
  * Fix: Display correct interlaced or progressive video scan type on activity cards.
  * New: Added flag for Nvidia hardware decoding on activity cards.
* Notifications:
  * Fix: Notification parameter prefix and suffix were not substituted correctly.
  * Fix: Release Date notification parameter was incorrectly casted to an integer instead of a string.
  * New: Added video scan type and full resolution notification parameters.
* UI:
  * Fix: Movies with the same title but different year being grouped on the homepage stats cards.
* API:
  * New: Added video scan type and full resolution values to get_activity command.
* Other:
  * Fix: Tautulli logging out every time after saving settings and restarting.


## v2.1.34 (2019-09-03)

* History:
  * New: Added Product column to history tables.
* Notifications:
  * Fix: IMDB/TMDb/TVDB/TVmaze ID notification parameters showing blank values after lookup.
* UI:
  * Fix: Libraries and Users tables did not respect the group history setting.
* API:
  * Fix: Title field was not searchable in get_library_media_info command.
  * New: Added grouping option to get_libraries_table and get_users_table commands.
  * New: Added product value to get_history command.
* Other:
  * Fix: Could not verify Plex Media Server with unpublished hostnames.
  * Change: Automatically logout all Tautulli instances when changing the admin password.


## v2.1.33 (2019-07-27)

* Notifications:
  * Change: Mask notification agent password fields.
  * Change: Enable searching by email address in dropdown menu.
* Other:
  * Fix: Version number being overwritten with "None" which prevented updating in some instances.
  * Change: Update Plex OAuth request headers.


## v2.1.32 (2019-06-26)

* Newsletters:
  * Fix: Newsletter scheduler issue for QNAP devices using an invalid "local" timezone preventing Tautulli from starting.


## v2.1.31 (2019-06-24)

* No additional changes from v2.1.31-beta.


## v2.1.31-beta (2019-06-13)

* Monitoring:
  * Fix: Synced content showing incorrect stream info.
* Other:
  * Fix: Unable to view database status when authentication is enabled.
  * Change: Default database synchronous mode changed to prevent database corruption. Database response may be slower.


## v2.1.30-beta (2019-05-11)

* Monitoring:
  * Fix: Activity crashing with Plex's Artist TV feature.
  * New: Added setting for Plex Media Server Update Check Interval. (Thanks @abiacco)
* Notifications:
  * New: Added secure and relayed connection notification parameters.
  * New: Added PLEX_USER_TOKEN to script environment variables.
  * Change: Schedule notifications using UTC to prevent missing notifications due to misconfigured timezones.
* API:
  * New: Added status API command to check the status of Tautulli.


## v2.1.29 (2019-05-11)

* No additional changes from v2.1.29-beta.


## v2.1.29-beta (2019-04-14)

* Monitoring:
  * Change: "Required Bandwidth" changed to "Reserved Bandwidth" in order to match the Plex dashboard.
* Notifications:
  * New: Added prefix and suffix notification text modifiers. See the "Notification Text Modifiers" help modal for details.
* UI:
  * New: Added "Undelete" button to the edit library and edit user modals.
  * Fix: User IP address history table showing incorrect "Last Seen" values.
* API:
  * Fix: Search API only returning 3 results.
  * Fix: Terminate stream API failing when both session_key and session_id were provided.
  * Change: Improved API response HTTP status codes and error messages.


## v2.1.28 (2019-03-10)

* Monitoring:
  * New: Added secure/insecure connection icon on the activity cards. Requires Plex Media Server v1.15+.
* Other:
  * Change: Improved mass deleting of all images from Cloudinary. Requires all previous images on Cloudinary to be manually tagged with "tautulli". New uploads are automatically tagged.


## v2.1.27-beta (2019-03-03)

* Monitoring:
  * Fix: Error when playing synced optimized versions.
  * Change: Show message to complete the setup wizard instead of error communicating with server message.
  * Change: URL changed on Plex.tv for Plex Media Server beta updates.
* Notifications:
  * New: Show the media type exclusion tags in the text preview modal.
  * Fix: Unicode error in the Email notification failed response message.
  * Fix: Error when a notification agent response is missing the "Content-Type" header.
* UI:
  * Fix: Usernames were not being sanitized in dropdown selectors.
  * Change: Different display of "All" recently added items on the homepage due to change in the Plex Media Server v1.15+ API.
* API:
  * New: Added current Tautulli version to update_check API response.
  * Change: API no longer returns sanitized HTML response data.
* Other:
  * New: Added auto-restart to systemd init script.
  * Fix: Patreon donation URL.
  * Remove: Crypto donation options.


## v2.1.26 (2018-12-01)

* Monitoring:
  * Fix: Resume event not being triggered after buffering.
* Notifications:
  * New: Added user email as a notification parameter.
* Graphs:
  * Fix: History model showing no results for stream info graph.
* API:
  * Fix: API returning error when missing a cmd.


## v2.1.25 (2018-11-03)

* Monitoring:
  * Fix: Audio and video codec showing up as * on the activity cards.
  * New: Poster and background image on the activity cards for live TV.
* UI:
  * Fix: Alert message for invalid Tautulli Public Domain setting.


## v2.1.24-beta (2018-10-29)

* Monitoring:
  * Fix: Transcode change events creating invalid sessions in the database.
* Notifications:
  * Change: Update Telegram character limit to 1024.
* History:
  * Fix: Save history table states separately for multiple Tautulli instances.
* Graphs:
  * Fix: Save graphs states separately for multiple Tautulli instances.
  * Change: Version graphs to bypass browser cache.
* UI:
  * New: Added queued tasks modals to the scheduled tasks table for debugging.
* Other:
  * Change: Updated timezone info and display in configuration table.


## v2.1.23-beta (2018-10-14)

* Monitoring:
  * Fix: Buffer events not being triggered properly.
  * Fix: Watched progress sometimes not saved correctly. (Thanks @Sheigutn)
* Notifications:
  * New: Added notification trigger for transcode decision change.
  * Fix: Multiple buffer notifications being triggered within the same second.
  * Change: Default buffer notification threshold changed to 10 for buffer thresholds less than 10.
* Newsletter:
  * New: Added Other Video libraries to the newsletter.
* Homepage:
  * New: Added Other Video type to recently added on the homepage.
  * Change: Save homepage recently added media type toggle state.
  * Change: Save homepage stats config to local storage instead of the server.
* History:
  * Change: Save history table media type toggle state.
* Graphs:
  * Change: Save series visibility state when toggling the legend.
  * Change: Save graph config to local storage instead of the server.
* UI:
  * New: Show the remote app device token and id in the edit device modal.
  * Change: Lock certain settings if using the Tautulli docker container.
* API:
  * Fix: download_config, download_database, download_log, and download_plex_log API commands not working.
  * Change: get_recently_added command 'type' parameter renamed to 'media_type'. Backwards compatibility is maintained.
  * Change: get_home_stats command 'stats_type' parameter change to string 'plays' or 'duration'. Backwards compatibility is maintained.


## v2.1.22 (2018-10-05)

* Notifications:
  * Fix: Notification agent settings not loading when failed to retrieve some data.
* UI:
  * Fix: Incorrectly showing localhost server in the setup wizard.
* Other:
  * Fix: Incorrect redirect to HTTP when HTTPS proxy header is present.
  * Fix: Websocket not connecting automatically after the setup wizard.


## v2.1.21 (2018-09-21)

* Notifications:
  * Fix: Content Rating notification condition always evaluating to True. (Thanks @Arcanemagus)
  * Fix: Script arguments not showing substituted values in the notification logs.
* UI:
  * New: Unsupported browser warning when using IE or Edge.
  * Fix: Misaligned refresh image icon in album search results. (Thanks @Sheigutn)
  * Fix: Music history showing as pre-Tautulli in stream info modal.
* Other:
  * Fix: Typo in Systemd init script group value. (Thanks @ldumont)
  * Fix: Execute permissions in Fedora/CentOS and Systemd init scripts. (Thanks @wilmardo)
  * Fix: Systemd init script instructions per Linux distro. (Thanks @samwiseg00)
  * Change: Fallback to Tautulli data directory if logs/backup/cache/newsletter directories are not writable.
  * Change: Check for alternative reverse proxy headers if X-Forwarded-Host is missing.


## v2.1.20 (2018-09-05)

* No additional changes from v2.1.20-beta.


## v2.1.20-beta (2018-09-02)

* Monitoring:
  * Fix: Fetch messing season info when "Hide Seasons" is enabled for a show.
  * Fix: Video and Audio details sometimes missing on activity cards.
* Notifications:
  * New: Added UTC timestamp to notification parameters. (Thanks @samwiseg00)
  * New: Added TAUTULLI_PUBLIC_URL to script environment variables. (Thanks @samwiseg00)
* UI:
  * Change: Automatically redirect '/' to HTTP root if enabled.
* API:
  * New: Added return_hash parameter to pms_image_proxy command.
  * New: Added session_id parameter to get_activity command.
* Other:
  * Change: Linux systemd startup script to use the "tautulli" group permission. (Thanks @samwiseg00)


## v2.1.19-beta (2018-08-19)

* Notifications:
  * New: Added Webhook notification agent.
  * Fix: Scripts failing due to unicode characters in substituted script arguments.
  * Change: Ability to override PYTHONPATH for scripts.
  * Remove: Notify My Android notification agent.
* Newsletters:
  * New: Added option for threaded newsletter emails.
  * Fix: Missing space in newsletter format.
* UI:
  * New: Added Windows system tray icon.
  * Fix: Plex OAuth not working with Plex remote access disabled. (Thanks @samwiseg00)
* API:
  * Fix: SQL command creating a database backup every time. (Thanks @samwiseg00)


## v2.1.18 (2018-07-27)

* Monitoring:
  * Fix: Progress bar on activity cards showing incorrect 100% when starting a stream.
* Notifications:
  * Fix: Notification text boxes scrolling to top when inputting text.
  * Change: Skip formatting invalid notification parameters instead of returning default text.
* UI:
  * Fix: Padding around search bar causing the navigation bar to break on smaller screens.


## v2.1.17-beta (2018-07-22)

* Notifications:
  * Change: Use default selected stream for media info in notifications.
* UI:
  * New: Automatically discover localhost Plex servers in server selection dropdown.
  * Change: Save Datatables state indefinitely.


## v2.1.16-beta (2018-07-06)

* Monitoring:
  * Fix: Plex server not detected as down during sudden network loss.
* Notifications:
  * Fix: Incorrect rounding of percentages in some cases.
  * Fix: Incorrect stream duration value for playback start notifications.
  * New: Added critic rating parameter for Rotten Tomatoes ratings.
* Newsletters:
  * Fix: Typo in "seasons" when there is only one additional season.
* UI:
  * New: Added ability to use Plex OAuth to login to Tautulli.
* API:
  * Fix: Unicode characters causing get_logs command to return bad data.
  * New: Added rating_image and audience_rating_image to get_activity and get_metadata commands.


## v2.1.15-beta (2018-07-01)

* Monitoring:
  * Fix: Progress percent displaying NaN for live TV.
  * Fix: Unable to terminate sessions with unicode characters in the message.
  * Change: Tizen platform to display the Samsung icon.
* Notifications:
  * New: Added PYTHONPATH to script environment variables so scripts can automatically import from Tautulli libraries.
  * Fix: Proper handling of unicode script arguments.
  * Fix: Incorrect TAUTULLI_URL environment variable if the HTTP host setting is changed.
  * Fix: Email addresses selectize box not expanding.
* Newsletters:
  * Change: HTTPS URLS for images hosted on tautulli.com.
* Graphs:
  * Fix: SD resolution sometimes not grouped together.


## v2.1.14 (2018-06-21)

* Notifications:
  * Fix: Parsing script arguments in quotes.
* UI:
  * Fix: Slow loading due to Font Awesome 5 javascript.
  * Change: Play counts on user an library pages now respect the history grouping setting.
* API:
  * New: Added optional grouping parameter to user and library watch statistics.


## v2.1.13 (2018-06-16)

* Monitoring:
  * Fix: Soft crash when viewing photos not in an album.
* Notifications:
  * New: Added current date and time notification parameters.
* UI:
  * New: Added support page with embedded Discord chat using WidgetBot.


## v2.1.12 (2018-06-08)

* Notifications:
  * Change: Blank notification link source means disabled instead of default.
* Newsletters:
  * New: Make collection tags available in the raw newsletter data for custom templates.
* API:
  * New: Ability to terminate a stream using the session key.


## v2.1.11-beta (2018-06-02)

* Monitoring:
  * Fix: Activity progress bar not updating in some cases.
  * Fix: Monitory Remote Access setting disabled due to Plex Media Server API changes.
  * Change: Improved logic for grouping history items without being successive plays.
* Notifications:
  * New: Added filename to notification parameters.
* Other:
  * Fix: Update metadata failing for tracks without track numbers.


## v2.1.10-beta (2018-05-28)

* Monitoring:
  * Fix: Improved monitoring of live tv sessions.
  * Change: Use track artist instead of album artist.
* Notifications:
  * New: Added timestamp to Discord notification embeds. (Thanks @samwiseg00)
  * New: Enable notifications for "clip" media types.
  * Fix: Actually add the "live" notification parameter.
  * Change: Update Twitter for 280 characters.
  * Change: Use HTTPS url for Cloudinary images.
* Newsletters:
  * Fix: Artist summaries not showing up on newsletter cards.
  * Change: Do not send the newsletter if the template fails to render.


## v2.1.9 (2018-05-21)

* Notifications:
  * New: Added "live" to notification parameters.


## v2.1.8-beta (2018-05-19)

* Newsletters:
  * New: Added authentication options for self-hosted newsletters.
  * Change: Check if the Tautulli footer has been removed in custom newsletter templates.
* Notifications:
  * Fix: Cloudinary images not working for Twitter notifications.
* API:
  * Fix: Return proper HTTP status codes for errors.


## v2.1.7-beta (2018-05-13)

* Newsletters:
  * New: Option to toggle between inline or internal CSS style templates.
  * New: Button to delete all uploaded images from Imgur/Cloudinary.
  * Fix: Long titles overflowing the newsletter cards.
  * Change: Self-hosted images on newsletters to use the /image endpoint instead of proxying through /newsletter/image.
  * Change: Strip whitespace from newsletter for smaller file size before sending to email.
* API:
  * New: Added get_stream_data command to API.
  * New: Added newsletter API commands to documentation.


## v2.1.6-beta (2018-05-09)

* Newsletters:
  * Change: Setting to specify static URL ID name instead of using the newsletter ID number.
  * Change: Reorganize newsletter config options.


## v2.1.5-beta (2018-05-07)

* Newsletters:
  * New: Added setting for a custom newsletter template folder.
  * New: Added option to enable static newsletter URLs to retrieve the last sent scheduled newsletter.
  * New: Added ability to change the newsletter output directory and filenames.
  * New: Added option to save the newsletter file without sending it to a notification agent.
  * Fix: Check for disabled image hosting setting.
  * Fix: Cache newsletter images when refreshing the page.
  * Fix: Refresh image from the Plex server when uploading to image hosting.
  * Change: Allow all image hosting options with self-hosted newsletters.
* UI:
  * Change: Don't retrieve recently added on the homepage if the Plex Cloud server is sleeping.
* Other:
  * Fix: Imgur database upgrade migration.


## v2.1.4 (2018-05-05)

* Newsletters:
  * Fix: Newsletter URL without an HTTP root.


## v2.1.3-beta (2018-05-04)

* Newsletters:
  * Fix: HTTP root doubled in newsletter URL.
  * Fix: Configuration would not open with failed hostname resolution.
  * Fix: Schedule one day off when using weekday names in cron.
  * Fix: Images not refreshing when changed in Plex.
  * Fix: Cloudinary upload with non-ASCII image titles.
* Other:
  * Fix: Potential XSS vulnerability in search.


## v2.1.2-beta (2018-05-01)

* Newsletters:
  * New: Added Cloudinary option for image hosting.
* Notifications:
  * New: Added Message-ID to Email header (Thanks @Dam64)
  * Fix: Posters not showing up on Twitter with self-hosted images.
  * Fix: Incorrect action parameter for new device notifications.
  * Change: Hardcode Pushover sound list instead of fetching the list every time.
* API:
  * Fix: Success result for empty response data.
  * Change: Do not send notification when checking for Tautulli updates via the API.


## v2.1.1-beta (2018-04-11)

* Monitoring:
  * Fix: Live TV transcoding showing incorrectly as direct play.
* Newsletters:
  * New: Added week number as parameter. (Thanks @samip5)
  * Fix: Fallback to cover art on the newsletter cards.
  * Change: Option to set newsletter time frame by calendar days or hours.
* Notifications:
  * New: Added week number as parameter. (Thanks @samip5)
* Other:
  * New: Added plexapi library for custom scripts.


## v2.1.0-beta (2018-04-07)

* Newsletters:
  * New: A completely new scheduled newsletter system.
    * Beautiful HTML formatted newsletter for recently added movies, TV shows, or music.
    * Send newsletters on a daily, weekly, or monthly schedule to your users.
    * Customize the number of days of recently added content and the libraries to include on the newsletter.
    * Add a custom message to be included on the newsletter.
    * Option to either send an HTML formatted email, or a link to a self-hosted newsletter on your own domain to any notification agent.
* Notifications:
  * New: Ability to use self-hosted images on your own domain instead of using Imgur.


## v2.0.28 (2018-04-02)

* Monitoring:
  * Fix: Homepage activity header text.


## v2.0.27 (2018-04-02)

* Monitoring:
  * Change: Move activity refresh interval setting to the settings page.


## v2.0.26-beta (2018-03-30)

* Monitoring:
  * New: Setting to change the refresh interval on the homepage.
  * Fix: Identify extras correctly on the activity cards.
* Notifications:
  * Change: Send Telegram image and text separately if the caption is longer than 200 characters.
* UI:
  * Fix: Error when clicking on synced playlist links.


## v2.0.25 (2018-03-22)

* Monitoring:
  * Fix: Websocket not reconnecting causing activity monitoring and notifications to not work.
  * Fix: Error checking for synced streams without Plex Pass.


## v2.0.24 (2018-03-18)

* Monitoring:
  * Fix: Fix stream data not showing for history recorded before v2.
* Notifications:
  * Fix: Set all environment variables for scripts.
  * Change: Moved all notification agent instructions to the wiki.
  * Change: XBMC notification agent renamed to Kodi.
  * Change: OSX Notify notification agent renamed to macOS Notification Center.


## v2.0.23-beta (2018-03-16)

* Monitoring:
  * Fix: Certain transcode stream showing incorrectly as direct play in history. Fix is not retroactive.
* Notifications:
  * New: Added season/episode/album/track count to notification parameters.
  * New: Added "Value 3" setting for IFTTT notifications.
  * New: Set PLEX_URL, PLEX_TOKEN, TAUTULLI_URL, and TAUTULLI_APIKEY environment variables for scripts.
  * Fix: Notifications failing to send with invalid custom conditions json.
  * Fix: Email notifications failing with unicode username/passwords.
  * Change: Facebook Graph API version updated to v2.12.
* UI:
  * New: Show the Plex Server URL in the settings.
  * Fix: Incorrect info displayed in the Tautulli login logs.
* API:
  * Fix: API returning empty data if a message was in the original data.
  * Change: get_server_id command returns json instead of string.
* Other:
  * Fix: Forgot git pull when changing branches in the web UI.


## v2.0.22 (2018-03-10)

* Tautulli v2 release!


## v2.0.22-beta (2018-03-09)

* Notifications:
  * Fix: Pushover notifications failing with priority 2 is set.
  * Fix: Expanding selectize box for some notification agent settings.
* Other:
  * Fix: Update check failing when an update is available.
  * Fix: Item count incorrect for photo libraries.


## v2.0.21-beta (2018-03-04)

* Monitoring:
  * New: Identify if a stream is using Plex Relay.
  * Change: Don't ping the Plex server if the websocket is disconnected.
* Notifications:
  * Fix: Pause/resume state not being sent correctly in some instances.
* Other:
  * New: Add Patreon donation method.
  * Fix: Catch failure to send analytics.
  * Fix: IP address connection lookup error when the country is missing.
  * Change: Updated all init scripts to Tautulli.
  * Change: Move database to tautulli.db.
  * Change: Move logs to tautulli.log.
  * Change: Move startup file to Tautulli.py.


## v2.0.20-beta (2018-02-24)

* Notifications:
  * New: Add poster support for Pushover notifications.
  * New: Add poster support for Pushbullet notifications.
  * Fix: Incorrect Plex/Tautulli update notification parameter types.
  * Change: Poster and text sent as a single message for Telegram.
  * Change: Posters uploaded directly to Telegram without Imgur.
* UI:
  * New: Add "Delete" button to synced items table on user pages.
  * Fix: Button spacing/positioning on mobile site.
  * Fix: Music statistic cards not using the fallback thumbnail.
  * Fix: Logo not showing up when using an SVG.
  * Change: Graphs now respect the "Group History" setting.
* API:
  * New: Add grouping to graph API commands.
* Other:
  * New: Added Google Analytics to collect installation metrics.
  * Fix: Reconnecting to the Plex server when server settings are not changed.


## v2.0.19-beta (2018-02-16)

* Monitoring:
  * Fix: Connect to Plex Cloud server without keeping it awake.
  * Fix: Reconnect to Plex Cloud server after the server wakes up from sleeping.
* Notifications:
  * Fix: Don't send Plex Server Up/Down notifications when Tautulli starts up.
  * Change: Better handling of Watched notifications.
* UI:
  * New: Added Plex server selection dropdown in the settings.
  * Fix: Libraries and Users tables not refreshing properly.
  * Change: Updated the masked info shown to guests.
  * Change: Check for updates without refreshing to the homepage.
* API:
  * New: Added update_check to the API.
  * Fix: delete_media_info_cache not deleting the cache.
  * Change: Document "refresh" parameter for get_library_media_info.
* Other:
  * Fix: Show the full changelog since v2 on a fresh install.


## v2.0.18-beta (2018-02-12)

* Notifications:
  * Fix: Default text for Tautulli update notifications using the wrong parameter.
  * Fix: Playback pause and resume notifications only triggering once.
  * Change: Negative operators for custom conditions now use "and" instead of "or".
* UI:
  * New: Added button to delete the 3rd party lookup info from the info pages.
  * Fix: Missing host info in the login logs when logging in using Firefox.
  * Change: Cleaned up settings. Advanced settings are now hidden behind a toggle.
* API:
  * New: Updated API documentation for v2.
* Other:
  * Fix: DeprecationWarning when using HTTPS with self-signed certificates.
  * Change: Deleting the Imgur poster URL also deletes the poster from Imgur (only available for new uploads).
  * Change: GitHub repository moved to Tautulli/Tautulli. Old GitHub URLs will still work.


## v2.0.17-beta (2018-02-03)

* Notifications:
  * Fix: Unable to use @ mentions tags for Discord and Slack.
  * New: Added Zapier notification agent.
* API:
  * Fix: get_synced_items returning no results.
  * Fix: get_library_media_info returning incorrect media type for photo albums.
  * Fix: get_library_media_info not being able to sort by title.


## v2.0.16-beta (2018-01-30)

* Monitoring:
  * Fix: Timestamp sometimes showing as "0:60" on the activity cards.
  * Fix: Incorrect session information being shown for playback of synced content.
  * Fix: Sessions not being stopped when "Playback Stopped" notifications were enabled.
* UI:
  * Fix: Stream resolution showing up as "unknown" on the graphs.
  * New: Added user filter to the Synced Items table.
* Other:
  * New: Option to use the Plex server update channel when checking for updates.


## v2.0.15-beta (2018-01-27)

* Monitoring:
  * Fix: Live TV sessions not being stopped in History.
  * Fix: Stream location showing as "unknown" on the activity cards.
  * New: Improved Live TV details on the activity cards.
* Notifications:
  * New: Added labels and collections to notification parameters.
  * New: Added more server details to notification parameters.
  * Change: Renamed "PlexPy" update notification parameters to "Tautulli".


## v2.0.14-beta (2018-01-20)

* Monitoring:
  * Change: Added "Cellular" bandwidth to "WAN" in activity header.
* Notifications:
  * Fix: Plex Web URL for tracks now go to the album page.
  * Fix: Recently added notifications being sent for the entire library when DVR EPG data was refreshed.
  * Fix: Notifier settings not loading with an apostrophe in the custom condition values.
  * Fix: Custom email addresses not being saved when closing the notifier settings.
  * Change: Re-enabled Browser notifications.
  * Change: Renamed "PlexPy" update notification parameters to "Tautulli".
  * Change: Emails no longer automatically insert HTML line breaks.
  * Change: "Date" header added to email notifications.
* UI:
  * Change: Show all changelogs since the previous version when updating.


## v2.0.13-beta (2018-01-13)

* Notifications:
  * New: Added dropdown selection for email addresses of shared users.
  * New: Added more notification options for Join.
  * Change: Show "OR" between custom condition values.
* Other:
  * New: Use JSON Web Tokens for authentication. Login now works with SSO applications.
  * New: Allow the Plex server admin to login as a Tautulli admin using their Plex.tv account.


## v2.0.12-beta (2018-01-07)

* Notifications:
  * Fix: Incorrect Plex URL parameter value.
  * Change: Custom condition logic is now optional. An implicit "and" is applied between all conditions if the logic is blank.
* UI:
  * New: Added separate required LAN/WAN bandwidth in the activity header.
* API:
  * Fix: Notify API command not sending notifications.


## v2.0.11-beta (2018-01-05)

* Notifications:
  * Fix: Some notification parameters showing up blank.
* UI:
  * Fix: Stream data showing up as "None" for pre-v2 history.
* Other:
  * Fix: Ability to login using the hashed password.


## v2.0.10-beta (2018-01-04)

* Monitoring:
  * Fix: HW transcoding indicator on activity cards incorrect after refreshing.
* Notifications:
  * Remove: Notification toggles from library and user settings. Use custom conditions to filter out notifications instead.
* UI:
  * Fix: Incorrect examples for some date format options. Also added a few missing date format options. (Thanks @Tommatheussen)


## v2.0.9-beta (2018-01-03)

* Notifications:
  * Fix: Notifications failing due to incorrect season/episode number types.


## v2.0.8-beta (2018-01-03)

* Monitoring:
  * Fix: Incorrect HW transcoding indicator on activity cards.
  * Fix: Long product/player names hidden behind platform icon on activity cards.
* Notifications:
  * Fix: Notifications failing due to some missing notification parameters.


## v2.0.7-beta (2018-01-01)

* Monitoring:
  * Fix: Incorrect LAN/WAN location on activity cards.
  * Fix: Paused time not recording correctly.
* Other:
  * Fix: Failed to retrieve synced items when there are special characters in the title.


## v2.0.6-beta (2017-12-31)

* Monitoring:
  * New: Beta Plex Cloud support.
  * Fix: Update paused time while still paused.
* UI:
  * Fix: Stopped time showing as "n/a" on history table.


## v2.0.5-beta (2017-12-31)

* Monitoring:
  * Fix: IPv6 addresses overflowing on the activity cards.
* Notifications:
  * Fix: Error sending Join notifications.
* UI:
  * New: Added total required bandwidth in the activity header.
* Other:
  * Fix: Failing to retrieve releases from GitHub.
  * Fix: CherryPy SSL connection warning. (Thanks @felixbuenemann)
  * Fix: Sanitize script output in logs.
  * Change: Login sessions persists across server restarts.


## v2.0.4-beta (2017-12-29)

* Monitoring:
  * Fix: Current activity cards duplicating on the homepage.
* Notifications:
  * Fix: Concurrent stream notifications being sent when there is an incorrect number of streams.
* UI:
  * New: Info pages for collections.
  * New: Button to test Plex Web URL override.
  * Fix: Library and User pages return to the correct tab when pressing back.


## v2.0.3-beta (2017-12-25)

* Monitoring:
  * Fix: Missing sync ID error causing logging to crash.
  * Fix: Incorrect optimized version title column name causing logging to crash.
* Notifications:
  * Fix: Report correct beta version for Tautulli update notifications.
* UI:
  * Fix: Missing CSS for stream info modal.


## v2.0.2-beta (2017-12-24)

* Monitoring:
  * Fix: Websocket connection fails to start with existing streams when upgrading to v2.
  * Fix: Long request URI for refreshing current activity on the homepage.
  * Fix: Missing subtitle database columns.
  * Fix: Details for synced and optimized versions reporting incorrectly.
* Notifications:
  * Fix: Recently added notifications sending for previously added items. It is now limited to past 24 hours only.
  * Fix: Source video/audio/subtitle parameters showing up as blank.
  * Change: Validate condition logic when saving a notification agent.
* API:
  * Change: API is enabled by default on new installs.
* UI:
  * New: Add logo svg files. (Thanks @Fish2)
  * New: Updated stream info modal.
  * Change: Media info tables sort by sort title instead of title.
* Other:
  * Fix: Updating library IDs message on libraries page.
  * Fix: Wtched percentage settings not saving after restart.
  * Remove: Video Preview Thumbnails setting no longer used.
  * Change: Add back HTTP Proxy setting under the Web Interface settings tab.
  * Change: "Group Table and Watch Statistics History" and "Current Activity in History Tables" enabled by default on new installs.


## v2.0.1-beta (2017-12-19)

* Monitoring:
  * Fix: Missing video_height database column.
* Notifications:
  * Fix: Join API key.
  * Change: Temporarily disable broken browser notifications.
* UI:
  * Fix: Incorrect fallback image for music watch statistics.


## v2.0.0-beta (2017-12-18)

* Monitoring:
  * New: More detailed stream info including subtitles, bitrates, bandwidth, and quality profiles.
  * New: Terminate sessions from the current activity (Plex Pass only).
  * Change: Monitoring uses websockets only now.
* Notifications:
  * New: Completely new notification system.
    * Allow adding multiple of the same notification agent and/or duplicating existing notification agents.
    * Each notification agent has it's own notification triggers and notification text.
    * Notification agents are stored in the database instead of the config file. Some notification configurations may have been lost in the transfer. Sorry.
  * New: Discord notification agent.
  * New: GroupMe notification agent.
  * New: MQTT notification agent.
  * New: More customizable info cards for Discord, Facebook, Hipchat, and Slack.
  * New: Script notifications are configured individually per script with separate arguments for each notification action.
  * New: Icon and duration options for Plex Home Theater and XBMC notifications.
  * New: Notification for Tautulli updates.
  * New: Added &lt;show&gt;, &lt;season&gt;, &lt;artist&gt;, and &lt;album&gt; notification exclusion tags.
    * &lt;tv&gt; is renamed to &lt;episode&gt;, and &lt;music&gt; is renamed to &lt;track&gt;
  * New: Preview notification text in the notifier settings.
  * New: Properly group recently added notifications when adding a batch of media.
    * The {season_num}, {episode_num}, and {track_num} parameters will be substituted with the range (e.g. 06-10)
  * New: Option to group recently added notifications by show/artist or season/album.
  * New: More detailed media info (video, audio, subtitle, file, etc.) notification options available.
  * New: Added notification text modifiers to change case and slice lists.
  * New: Custom notification conditions using parameters to filter notifications.
  * New: Button to trigger manual recently added notifications from the info pages.
  * New: Lookup TVMaze and TheMovieDatabase links.
  * Remove: The shared Imgur client ID has been removed. Please enter your own client ID in the settings to continue uploading posters.
  * Change: Notifications with a blank subject or body will no longer be sent at all.
  * Change: Line breaks inserted automatically in Email notification text.
  * Change: Notifications for season/episodes now use the season poster and album/track now use the album art.
  * Change: The {action} parameter is no longer capitalized.
  * Change: Notification success or failure added to notification logs.
* API:
  * New: Added check for Plex Media Server updates with the Tautulli API.
  * New: Added show/artist and episode/track titles to the "get_history" API command.
  * New: Added manual trigger for recently added notifications.
  * Remove: Defunct API v1.
  * Change: The "notify" API command now requires a notifier_id instead of an agent_id. The notifier ID can be found in the settings for each notification agent.
  * Change: The returned json for the "get_metadata" API command is no longer nested under the "metadata" key.
* UI:
  * New: Updated current activity, watch statistics, and library statistics cards on the home page.
  * New: Toggle stats and recently added categories directly on the homepage.
  * New: Ability to delete synced items from the Synced Items page.
  * New: Updated platform icons to a uniform style.
  * Remove: Setting for number of top items for watch statistic cards.
  * Change: Separate API and websocket logs.
* Android Tautulli Remote App (beta):
  * New: Download the Tautulli Remote app on Google Play!
    * Link the app using a QR code in the Tautulli settings.
  * New: Push notifications directly to the Tautulli Remote app.
* Other:
  * New: Option to update Tautulli automatically when an update is available.
  * New: Option to switch the tracking git remote and branch.
  * New: Option to change the path to your git environment variable.
  * New: Option to use a HTTPS certificate chain.
  * New: Option to override the Plex Web URL for click-through links.
  * New: Separate watched percentage for movies, episodes, and tracks.
  * New: Show changelog after updating Tautulli.
  * New: Support for IPv6 geolocation lookup.
  * New: Download the Tautulli configuration file or database from the settings.
  * New: Log failed Tautulli login attempts.
  * Fix: Modal popups not working on mobile Safari.
  * Fix: Prevent password managers from autofilling the password in the settings.
  * Fix: Unable to search with special characters.
  * Remove: Some unused options have been removed from the settings page.
  * Change: The database schema has been changed, and reverting back to PlexPy v1 will not work.
  * Change: The dev branch has been depreciated. A master/beta/nightly system is used instead.

  
## v1.4.25 (2017-10-02)

* Fix: Tab instead of spaces preventing startup.


## v1.4.24 (2017-10-01)

* Fix: New Plex Web urls. (Thanks @Joshua1337)
* Fix: Fallback to the product name if the player title is blank.
* New: Added no forking option to startup arguments. (Thanks @Vashypooh)


## v1.4.23 (2017-09-30)

* Fix: Playstation 4 platform name.
* Fix: PlexWatch and Plexivity import.
* Fix: Pushbullet authorization header.


## v1.4.22 (2017-08-19)

* Fix: Cleaning up of old config backups.
* Fix: Temporary fix for incorrect source media info.


## v1.4.21 (2017-07-01)

* New: Updated donation methods.


## v1.4.20 (2017-06-24)

* New: Added platform image for the PlexTogether player.
* Fix: Corrected math used to calculate human duration. (Thanks @senepa)
* Fix: Sorting of 4k in media info tables.
* Fix: Update file sizes when refreshing media info tables.
* Fix: Support a custom port for Mattermost (Slack) notifications.


## v1.4.19 (2017-05-31)

* Fix: Video resolution not showing up for transcoded streams on PMS 1.7.x.


## v1.4.18 (2017-04-22)

* New: Added some new Arnold quotes. (Thanks @senepa)
* Fix: Text wrapping in datatable footers.
* Fix: API command get_apikey. (Thanks @Hellowlol)


## v1.4.17 (2017-03-04)

* New: Configurable month range for the Plays by month graph. (Thanks @Pbaboe)
* New: Option to chanage the week to start on Monday for the the Plays by day of week graph. (Thanks @Pbaboe)
* Fix: Invalid iOS icon file paths. (Thanks @demonbane)
* Fix: Plex Web 3.0 URLs on info pages and notifications.
* Fix: Update bitcoin donation link to Coinbase.
* Fix: Update init scripts. (Thanks @ampsonic)


## v1.4.16 (2016-11-25)

* Fix: Websocket for new json response on PMS 1.3.0.
* Fix: Update stream and transcoder tooltip percent.
* Fix: Typo in the edit user modal.


## v1.4.15 (2016-11-11)

* New: Add stream and transcoder progress percent to the current activity tooltip.
* Fix: Refreshing of images in the cache when authentication is disabled.
* Fix: Plex.tv authentication with special characters in the username or password.
* Fix: Line breaks in the info page summaries.
* Fix: Redirect to the proper http root when restarting.
* Fix: API result type and responses showing incorrectly. (Thanks @Hellowlol)
* Change: Use https URL for app.plex.tv.
* Change: Show API traceback errors in the browser with debugging enabled. (Thanks @Hellowlol)
* Change: Increase table width on mobile devices and max width set to 1750px. (Thanks @XusBadia)


## v1.4.14 (2016-10-12)

* Fix: History logging locking up if media is removed from Plex before PlexPy can save the session.
* Fix: Unable to save API key in the settings.
* Fix: Some typos in the settings. (Thanks @Leafar3456)
* Change: Disable script timeout by setting timeout to 0 seconds.


## v1.4.13 (2016-10-08)

* New: Option to set the number of days to keep PlexPy backups.
* New: Option to add a supplementary url to Pushover notifications.
* New: Option to set a timeout duration for script notifications.
* New: Added flush temporary sessions button to extra settings for emergency use.
* New: Added pms_image_proxy to the API.
* Fix: Insanely long play durations being recorded when connection to the Plex server is lost.
* Fix: Script notification output not being sent to the logger.
* Fix: New libraries not being added to homepage automatically.
* Fix: Success message shown incorrectly when sending a test notification.
* Fix: PlexPy log level filter not working.
* Fix: Admin username not shown in login logs.
* Fix: FeatHub link in readme document.
* Change: Posters disabled by default for all notification agents.
* Change: Disable manual changing of the PlexPy API key.
* Change: Force refresh the Plex.tv token when fetching a new token.
* Change: Script notifications run in a new thread with the timeout setting.
* Change: Watched percent moved to general settings.
* Change: Use human readable file sizes to the media info tables. (Thanks @logaritmisk)
* Change: Update pytz library.


## v1.4.12 (2016-09-18)

* Fix: PMS update check not working for MacOSX.
* Fix: Square covers for music stats on homepage.
* Fix: Card width on the homepage for iPhone 6/7 Plus. (Thanks @XusBadia)
* Fix: Check for running PID when starting PlexPy. (Thanks @spolyack)
* Fix: FreeBSD service script not stopping PlexPy properly.
* Fix: Some web UI cleanup.
* Change: GitHub repostitory moved.


## v1.4.11 (2016-09-02)

* Fix: PlexWatch and Plexivity import errors.
* Fix: Searching in history datatables.
* Fix: Notifications not sending for Local user.


## v1.4.10 (2016-08-15)

* Fix: Missing python ipaddress module preventing PlexPy from starting.


## v1.4.9 (2016-08-14)

* New: Option to include current activity in the history tables.
* New: ISP lookup info in the IP address modal.
* New: Option to disable web page previews for Telegram notifications.
* Fix: Send correct JSON header for Slack/Mattermost notifications.
* Fix: Twitter and Facebook test notifications incorrectly showing as "failed".
* Fix: Current activity progress bars extending past 100%.
* Fix: Typo in the setup wizard. (Thanks @wopian)
* Fix: Update PMS server version before checking for a new update.
* Change: Compare distro and build when checking for server updates.
* Change: Nicer y-axis intervals when viewing "Play Duration" graphs.


## v1.4.8 (2016-07-16)

* New: Setting to specify PlexPy backup interval.
* Fix: User Concurrent Streams Notifications by IP Address checkbox not working.
* Fix: Substitute {update_version} in fallback PMS update notification text.
* Fix: Check version for automatic IP logging setting.
* Fix: Use library refresh interval.


## v1.4.7 (2016-07-14)

* New: Use MaxMind GeoLite2 for IP address lookup.
  * Note: The GeoLite2 database must be installed from the settings page.
* New: Check for Plex updates using plex.tv downloads instead of the server API.
  * Note: Check for Plex updates has been disabled and must be re-enabled in the settings.
* New: More notification options for Plex updates.
* New: Notifications for concurrent streams by a single user.
* New: Notifications for user streaming from a new device.
* New: HipChat notification agent. (Thanks @aboron)
* Fix: Username showing as blank when friendly name is blank.
* Fix: Direct stream count wrong in the current activity header.
* Fix: Current activity reporting direct stream when reducing the stream quality switches to transcoding.
* Fix: Apostophe in an Arnold quote causing the shutdown/restart page to crash.
* Fix: Disable refreshing posters in guest mode.
* Fix: PlexWatch/Plexivity import unable to select the "grouped" database table.
* Change: Updated Facebook notification instructions.
* Change: Subject line optional for Join notifications.
* Change: Line break between subject and body text instead of a colon for Facebook, Slack, Twitter, and Telegram.
* Change: Allow Mattermost notifications using the Slack config.
* Change: Better formatting for Slack poster notifications.
* Change: Telegram only notifies once instead of twice when posters are enabled.
* Change: Host Open Sans font locally instead of querying Google Fonts.


## v1.4.6 (2016-06-11)

* New: Added User and Library statistics to the API.
* New: Ability to refresh individual poster images without clearing the entire cache. (Thanks @Hellowlol)
* New: Added {added_date}, {updated_date}, and {last_viewed_date} to metadata notification options.
* New: Log level filter for Plex logs. (Thanks @sanderploegsma)
* New: Log level filter for PlexPy logs.
* New: Button to download Plex logs directly from the web interface.
* New: Advanced setting in the config file to change the number of Plex log lines retrieved.
* Fix: FreeBSD and FreeNAS init scripts to reflect the path in the installation guide. (Thanks @nortron)
* Fix: Monitoring crashing when failed to retrieve current activity.


## v1.4.5 (2016-05-25)

* Fix: PlexPy unable to start if failed to get shared libraries for a user.
* Fix: Matching port number when retrieving the PMS url.
* Fix: Extract mapped IPv4 address in Plexivity import.
* Change: Revert back to internal url when retrieving PMS images.


## v1.4.4 (2016-05-24)

* Fix: Image queries crashing the PMS when playing clips from channels.
* Fix: Plexivity import if IP address is missing.
* Fix: Tooltips shown behind the datatable headers.
* Fix: Current activity instances rendered in a random order causing them to jump around.


## v1.4.3 (2016-05-22)

* Fix: PlexPy not starting without any authentication method.


## v1.4.2 (2016-05-22)

* New: Option to use HTTP basic authentication instead of the HTML login form.
* Fix: Unable to save settings when enabling the HTTP proxy setting.
* Change: Match the PMS port when retrieving the PMS url.


## v1.4.1 (2016-05-20)

* New: HTTP Proxy checkbox in the settings. Enable this if using an SSL enabled reverse proxy in front of PlexPy.
* Fix: Check for blank username/password on login.
* Fix: Persist current activity artwork blur across refreshes when transcoding details are visible.
* Fix: Send notifications to multiple XBMC/Plex Home Theater devices.
* Fix: Reset PMS identifier when clicking verify server button in settings.
* Fix: Crash when trying to group current activity session in database.
* Fix: Check current activity returns sessions when refreshing.
* Fix: Logs sorted out of order.
* Fix: Resolution reported incorrectly in the stream info modal.
* Fix: PlexPy crashing when hashing password in the config file.
* Fix: CherryPy doubling the port number when accessing PlexPy locally with http_proxy enabled.
* Change: Sort by most recent for ties in watch statistics.
* Change: Refresh Join devices when changing the API key.
* Change: Format the Join device IDs.
* Change: Join notifications now sent with Python Requests module.
* Change: Add paging for recently added in the API.


## v1.4.0 (2016-05-15)

* New: An HTML form login page with sessions support.
* New: Guest access control for shared users using Plex.tv authentication.
  * Enable the option in the settings and toggle guest access per user from Users > Edit mode.
  * Guests can only view their own user data. Other user info is removed/masked.
  * Guests can only view media from libraries that are shared with them (content rating and label filters are respected). Other libraries are removed/masked.
  * All settings and admin controls are restricted from guests.
  * All current activity on the server is shown, but with masked user/metadata info.
* New: Login logs table on the User and Logs pages.
* New: Filter the history table by user.
* New: Filter the graphs by user. (Thanks @Otger)
* New: Option to hash the admin passowrd in the config file.
* New: Options to enable/disable/rearrange each section on the homepage
* New: Toggle media types for recently added items on the homepage.
* New: Option to enter an Imgur API client ID for uploading posters.
  * Note: The shared Imgur client id will be removed in a future PlexPy update! Please enter your own client id in the settings to continue uploading posters!
* New: HTML support for Email.
* New: Posters and HTML support for Telegram.
* New: Poster support for Slack.
* New: Poster support for Twitter.
* New: Re-added Plex Home Theater notification agent.
* New: Browser notification agent (experimental).
* New: Added {plex_url} as a notification option.
* New: Added transcode decision to the activity header.
* New: Documentation for APIv2 (see API.md for details).
* New: Import a Plexivity database into PlexPy.
* New: Prettier fallback image for art/episodes.
* New: Prettier confirm modal dialogues.
* New: Cache images to reduce Plex API calls. This can be disabled in the under Settings > Extra Settings. (Thanks @Hellowlol)
* New: Scheduled backups of the config file.
* New: Button to clear the PlexPy cache/images in the settings.
* New: Button to manually backup the PlexPy database/config in the settings.
* New: Button to clear the PlexPy logs in the settings.
* New: Button to download PlexPy log file on the Logs tab.
* New: Advanced setting in config file to change the Plex API timeout value.
* Fix: Mixed content HTTP request in settings (for reverse proxies with SSL).
* Fix: Rename recently "watched" music to "played".
* Change: Current activity details now persists across refreshes.
* Change: Smoother transitions between preview thumbnails in current activity.
* Change: Datatables now display all columns and scroll horizontally on smaller screens.
* Change: Ability to change the base URL for reverse proxies in the web interface.
* Change: Added a "Verify Server" button in the settings.
* Change: Added request status code in the logs for notifer errors.
* Change: Remove in-memory logs and read lines from log file instead. (Thanks @Hellowlol)
* Change: Limit number of failed attempts to write sessions to history. Default is 5 attempts.
* Change: A bunch of UI updates.
* Change: A bunch of backend code cleanup.
* Removed: All unused Python packages.


## v1.3.16 (2016-05-01)

* Fix: Viewing photos crashing PlexPy.
* Fix: Persist Users > Edit mode on datatable page change.
* Fix: PMS update notifications broken.
* Change: Cache notifications poster with thread ID to avoid overwritting images.


## v1.3.15 (2016-04-18)

* Fix: Slack notifications failing when using and icon URL.
* Fix: 127.0.0.1 showing as an external IP address on the history tables.
* Fix: Regression file sizes not shown in the media info table footer.
* Fix: Retrieving proper PMS URL when multiple connections are published to plex.tv.
* Fix: Some typos in the logger.
* Fix: Some other typos in the WebUI. (Thanks @xtjoeytx)
* Change: Optimized mobile web app icons and spash screens. (Thanks @alotufo)


## v1.3.14 (2016-03-29)

* Fix: Regression for missing notify_action for script notifications.
* Fix: Typo for home stats cards in the settings.


## v1.3.13 (2016-03-27)

* Fix: Only mask strings longer than 5 characters in logs.


## v1.3.12 (2016-03-27)

* Fix: "Check GitHub for updates" not rescheduling when toggling setting.
* Fix: Bug where notifications would fail if metadata is not found.
* Fix: Bug where notifications would fail if unable to upload poster to Imgur.
* Fix: PlexPy will now start properly for different Python environment variables.
* New: Feature requests moved to FeatHub.
* New: Ability to specify a GitHub API token for updates (optional).
* New: Mask out sensitive information from the logs.
* New: New and updated Arnold quotes. (Thanks @Vilsol & @Chrisophogus)
* New: "First" and "Last" page buttons to datatables.
* New: Access log file from the "Help & Info" page.
* New: CherryPy environment options (for development). (Thanks @codedecay)
* New: PlexPy development environment (for development only).
* Change: Facebook posts with a posters now include a summary.
* Change: Facebook posts now use a default poster if the poster is not found or unable to upload to Imgur.
* Change: IFTTT events can be fromatted with the {action} name.
* Change: Logs now use ISO date format to avoid locale encoding errors. (Thanks @alshain)
* Remove: Non-functioning Plex notification agent.


## v1.3.11 (2016-03-15)

* Fix: Typo preventing history logging for websockets.


## v1.3.10 (2016-03-12)

* Fix: Actually allow HTML tags for Pushover.
* Fix: PlexPy not restarting on Windows if there is a space in the folder path.
* Fix: Reconnect websocket when changing PMS SSL setting.
* Fix: Datatables not loading when view_offset or duration is blank.
* Fix: Bug when checking the PMS version in the settings.
* Fix: Auto-refreshing of log tables.
* Fix: Logging of IPv6 addresses. (PMS version >0.9.14 only.)
* Fix: Hide days selection from the Play Totals graph page.
* Fix: PlexPy overwriting user's own SSL certificate/key.
* Fix: Multiple watched notifications when using websocket.
* Fix: Some missing python library imports.
* Fix: Some typos in settings and PlexWatch importer.
* New: Ability to get notified of PMS updates.
* New: Ability to disable the link to Plex Web with Facebook notifications and use IMDB, TVDB, TMDb, or Last.fm instead.
* New: Ability to reset Imgur poster url from the info page if the poster is changed.
* New: Tooltips on the current activity progress bars.
* New: Side scrolling of Recently Added/Recently Played items.
* New: Document all date/time format options.
* New: Button to clear notification logs.
* New: Customizable backup, cache, and log directories.
* Change: Retry writing sessions to history if it fails, so sessions don't get lost. (Activity pinger only, not availble for websocket.)
* Change: Save any unknown sessions to the "Local" user.
* Change: History table modal is filtered depending on which graph series is clicked.
* Change: Revert back to saving the state of datatables (search, sorting, entries per page, etc.).
* Change: Newlines are not longer stripped from notification text which allows for finer control of how notifications look.
* Change: Updated FreeNAS/FreeBSD init scripts. (Must have updated jails.) (Thanks @chiviak)


## v1.3.9 (2016-02-21)

* Fix: Recently added notification not sent to all notification agents.
* New: Pushover HTML support. (Thanks @elseym)


## v1.3.8 (2016-02-21)

* Fix: Regression unable to clear HTTP password.
* Fix: Remove media tags from script arguments for server notifications.
* Fix: Encode poster titles to UTF-8 for Imgur upload.
* Fix: Allow notifications to send without poster if Imgur upload fails.
* New: Notification Logs table in the Logs tab.
* New: Toggle in settings to enable posters in notifications. (Disabled by default.)
* Change: Save Imgur poster URL to database so upload is not needed every time.
* Change: Notify log in database to log each event as a separate entry.
* Change: Monitor remote access is unchecked if remote access is disabled on server.


## v1.3.7 (2016-02-20)

* Fix: Verifying server with SSL enabled.
* Fix: Regression where {stream_duration} reported as 0.
* Fix: Video metadata flags showing up for track info.
* Fix: Custom library icons not applied to Library Statistics.
* Fix: Typos in the Web UI.
* New: ETA to Current Activity overlay.
* New: Total duration to Libraries and Users tables.
* New: {machine_id} to notification options.
* New: IMDB, TVDB, TMDb, Last.fm, and Trackt IDs/URLs to notification options.
* New: {poster_url} to notification options using Imgur.
* New: Poster and link for Facebook notifications.
* New: Log javascript errors from the Web UI.
* New: Configuration and Scheduler info to the settings page.
* New: Schedule background task to backup the PlexPy database.
* New: URL anonymizer for external links.
* New: Plex Media Scanner log file to Log viewer.
* New: API v2 (sill very experimental). (Thanks @Hellowlol)
* Change: Allow secure websocket connections.
* Change: History grouping now accounts for the view offset.
* Change: Subject line can be toggled off for Facebook, Slack, Telegram, and Twitter.
* Change: Create self-signed SSL certificates when enabling HTTPS.
* Change: Revert homepage "Last Played" to "Last Watched".
* Change: Disable monitor remote access checkbox if remote access is not enabled on the PMS.
* Change: Disable IP logging checkbox if PMS version is 0.9.14 or greater.


## v1.3.6 (2016-02-03)

* Fix: Regression where {duration} not reported in minutes.
* Fix: Proper daemonizing in FreeBSD and FreeNAS init scripts.
* Change: Update readme documentation.


## v1.3.5 (2016-02-02)

* Fix: Removing unique constraints from database.
* Fix: Unable to expand media info table when missing "Added At" date.
* Fix: Server verification for unpublished servers.
* Fix: Updating PMS identifier for server change.
* New: {stream_time}, {remaining_time}, and {progress_time} to notification options.
* New: Powershell script support. (Thanks @Hellowlol)
* New: Method to delete duplicate libraries.
* Change: Daemonize before running start up tasks.


## v1.3.4 (2016-01-29)

* Fix: Activity checker not starting with library update (history not logging).
* Fix: Libraries duplicated in database.
* Fix: Buffer notifications even when disabled when using websockets.
* Fix: Libraries and Users lists not refreshing.
* Fix: Server verification in settings.
* Fix: Empty libraries not added to database.
* New: Unique identifiers to notification options.
* Remove: Requirement of media type toggles for recently added notifications.
* Remove: Built in Twitter key and secret.
* Change: Unnecessary quoting of script arguments.
* Change: Facebook notification instructions.


## v1.3.3 (2016-01-26)

* Fix: Plays by Month graph not loading.
* Change: Disable caching for datatables.
* Change: Improved updating library data in the database again.


## v1.3.2 (2016-01-24)

* Fix: 'datestamp' and 'timestamp' for server notifications.
* Change: New method for updating library data in database.


## v1.3.1 (2016-01-23)

* Fix: Notifiers authorization popups for reverse proxies.
* Fix: Empty brackets in titles on tables.
* Fix: Star rating overlapping text.
* Fix: Unable to startup when library refresh fails.
* Fix: Unable to parse 'datestamp' and 'timestamp' format.
* Change: Rename "Last Watched" to "Last Played".
* Change: More descriptive libraries updating message.


## v1.3.0 (2016-01-23)

* New: Brand new Libraries section.
* New: Lots of new library statistics.
* New: Media info table for libraries.
* New: Web app for Android and iOS. (Thanks @zobe123)
* New: Slack notification agent. (Thanks @richipargo)
* New: Facebook notification agent.
* New: Custom script notification agent. (Thanks @Hellowlol)
* New: Custom "From Name" to email notification agent.
* New: Ability to test notifications / send custom one-off notifications.
* New: 'datestamp' and 'timestamp' notification options.
* New: More concurrent stream statistics.
* New: Media info flags on the info pages.
* New: Ability to fix broken metadata if the item has been moved in Plex.
* New: Ability to rearrange the homepage statistics cards.
* New: CentOS startup script (Thanks @PHoSawyer)
* Fix: Server name blank after first run wizard.
* Fix: Incorrect duration for grouped home stats.
* Fix: Allow SSL when verifying server in settings.
* Fix: Metadata for grouped recently added notifications.
* Fix: Unable to access settings with missing changelog file.
* Fix: Month name localization on play totals graphs.
* Fix: Get new PMS identifier when changing servers.
* Fix: Websocket log spam when there is no active session.
* Fix: Logs and cache folder not created in the data directory.
* Fix: Title links on sync table.
* Fix: Other various minor bugs and graphical glitches.
* Change: Prettier thumbnail popovers on tables.
* Change: Star ratings to use css/font-awesome.
* Change: More detailed logging info to warnings and errors.
* Change: Better PlexPy process restart handling (Thanks @jackwilsdon)
* Change: Massive behind the scenes code cleanup.
* Remove: Built in Pushover API token (User's own API token is now required).


## v1.2.16 (2015-12-22)

* Fix Most Concurrent stream stat for emtpy databases
* Change logs to 50 lines by default


## v1.2.15 (2015-12-20)

* Fix navbar covering current activity on smaller screens.
* Fix metadata for grouped recently added notifications.
* Fix Growl notification agent not working.
* Change graph days selection.
* Change watch statistics to match table history grouping.
* Add automatic discovery of Pushbullet devices.
* Add Most Concurrent Streams watch statistic.
* Add precentage to current activity progress bars.
* Add a bunch of stream details to notification options.
* Add notification for Plex Remote Access/Plex Media Server back up.
* Add CC/BCC and multiple recipients to email notification agent.
* Add total watch time to history table footer.


## v1.2.14 (2015-12-07)

* Fix regression with PlexWatch db importer and buffer warnings.


## v1.2.13 (2015-12-06)

* Fix match newlines between tags in notification text.
* Fix current activity not showing on PMS 0.9.12.


## v1.2.12 (2015-12-06)

* Fix for "too many open files" error.


## v1.2.11 (2015-12-06)

* Fix more regressions (sorry).


## v1.2.10 (2015-12-06)

* Fix broken count graphs regression.


## v1.2.9 (2015-12-06)

* Fix and improve text sanitization.


## v1.2.8 (2015-12-06)

* Fix sanitize player names
* Fix recently added notification delay
* Fix recently added metadata queries
* Fix multiple lines in notification body text
* Fix UTF-8 encoding in Prowl notifications subject line
* Change to only log IPv4 addresses
* Add global toggle for recently added notifcations
* Add feature to delete users
* Add channel support for Telegram notification agent
* Add icon for Apple tvOS
* Add icon for Microsoft Edge


## v1.2.7 (2015-11-27)

* Fix IP address option in notifications


## v1.2.6 (2015-11-27)

* Fixes for IP logging in PMS < 0.9.14.x.
* Fix issue in plexWatch importer when trying to import item with no ratingKey.


## v1.2.5 (2015-11-25)

* Add video_decision and audio_decision to notification options
* Fix IP address logging
* Fix log spam if notifications disabled 


## v1.2.4 (2015-11-24)

* Add filtering by media type in the history table
* Add IFTTT notification agent
* Add Telegram notification agent
* Add notifications for recently added media
* Add notifications for server down and remote access down
* Add more metadata to notifications options
* Add IP address to notification options (for PMS 0.9.14 and above)
* Add server uptime to notification options
* Add IP address to current activity
* Add IPv6 address logging
* Add PMS server name to the page title
* Fix bug in "Last Watched" statistic
* Fix bug in search query
* Fix bug on user pages for usernames with single quotes
* Fix name for new Plex Media Center
* Fix Pushover notifications with unicode characters
* Fix bug with showing old usernames in datatables
* Fix bug with "Please verify your server" in settings
* Change IP lookup provider
* Change notifications custom body text to larger text box
* Change movie/tv logging and notifications into individual options


## v1.2.3 (2015-10-18)

* Added "remaining time" as notification substitution.
* Fix bug on home stats cards.
* Fix visual bug on user page.


## v1.2.2 (2015-10-12)

* Add server discovery on first run.
* Add column to tables for Platform.
* Add link to top level breadcrumbs on info pages.
* Add ability to change notification sounds for Pushover and Boxcar.
* Show watched percentage tooltip on progress column in history tables. 
* More logging in event an http request fails.
* Code cleanups and other fixes.
* Fix ordering on sync table.
* Fix bug on home stats cards.
* Fix bug on activity pane where music details were not shown.


## v1.2.1 (2015-09-29)

* Fix for possible issue when paused_counter is null.


## v1.2.0 (2015-09-29)

* Added option to group consecutive plays in the history tables.
* Added option for websocket monitoring (still slightly experimental and disabled by default).
* Added global search option (searches your Plex library).
* Added option to update any items that may have had their rating keys changed.
* Added option to disable consecutive notifications. 
* Some visual tweaks and fixes.
* Fix bug where monitoring wouldn't start up after first run.
* Fix bug showing incorrect transcode decisions for music tracks on history tables.


## v1.1.10 (2015-09-20)

* Added dedicated settings section for home stats configuration with ability to show/hide selected stats and sections.
* Added support for Twitter notifications.
* Only show music in graphs if music logging is enabled.
* The monitoring ignore interval now excludes paused time. 
* Fix display bug on activity panel which incorrectly reported transcoding sometimes.
* Fix bug with Email notification TLS checkbox when it would be disabled by changing any other settings afterwards.
* Fix issue on some Python releases where the webbrowser library isn't included.


## v1.1.9 (2015-09-14)

* Another JonnyWong release. I'm going to stop thanking you now ;)
* Add music plays to graphs.
* Add info pages for music items.
* Add music to user recently watched items.
* Add photo views to Activity pane (photos are not logged).
* Fix token validation message on Settings page.
* Fix some "Mystery" platform names.
* Fix paused time be counted for graph data.
* Other small bug fixes.


## v1.1.8 (2015-09-09)

* Add platform images for Windows devices. Thanks @JonnyWong.
* Add click-through to PlexWeb preplay page from info page. Thanks @JonnyWong. 
* Fix broken delete option on info pages. Thanks @JonnyWong.
* Fix tagline bug in PlexWatch db import tool.
* Fix home stats text overflow bug. Thanks @JonnyWong.


## v1.1.7 (2015-09-07)

* Show tagline in info screens for movies. Thanks @JonnyWong.
* Add play/pause/buffer icon to activity pane. Thanks @JonnyWong.
* Add transcoder info in activity pane info. Thanks @JonnyWong.
* Show transcoder progress on activity progress bar. Thanks @JonnyWong.
* Fix bug where custom notification strings would be ignored if unicode characters were present.
* Fix text overflow issue on home stats cards. Thanks @JonnyWong.
* Fix regression with user friendly name change input in edit screen. Thanks @JonnyWong.


## v1.1.6 (2015-09-06)

* Home stats cards are now expandable to show multiple items. Configurable in settings. Thanks @JonnyWong.
* Completely redesigned media info pages. Thanks @JonnyWong.
* Redesigned activity pane to match Plex Web more closely. Thanks @JonnyWong.
* New Library stats on home page, shows total item counts per library. Thanks @JonnyWong.
* New last watched card in home stats. Shows last watched items. Thanks @JonnyWong.
* Improved some layout issues on mobile devices. Thanks @JonnyWong.
* Fixed issue where some clip/channel items are reported as episodes and causing exceptions.
* Many styling improvements and fixes. Thanks @JonnyWong.
* Fixed incorrect sort on home stats platform count by duration. Thanks @JonnyWong.
* Fix issue where user refresh would continually be called as "Local" user didn't exist in database.
* Fixed styling on graph stream modal. Thanks @JonnyWong.
* Fixed some issues with users page editing. Thanks @JonnyWong.
* Fix error page when clicking through to an item that no longer exists.


## v1.1.5 (2015-08-27)

* Fix git tag being one release behind.


## v1.1.4 (2015-08-26)

* User info is now editable from the users table. Thanks @JonnyWong.
* Improved delete mode for history pages - able to multi-select now. Thanks @JonnyWong.
* Improved image quality on tooltip images.
* More styling improvements and fixes on user and info pages. Thanks @JonnyWong.
* Added some user submitted systemd init scripts. Thanks @malle-pietje and @artbird309.
* Fixed some background operations when saving settings.
* Fix max width restricting home stats to 1600px.
* Fix stream duration parameter for notifications when paused counter is null.


## v1.1.3 (2015-08-22)

* Show human readable version info and this cool changelog in Settings -> General.
* Add a "delete" mode to the history tables. Toggle it to show a delete button next to each history item.
* Two digit season and episode numbers for custom notification messages. Thanks @JonnyWong.
* New FreeNAS init script. Thanks @JonnyWong.
* Lots of styling improvements! Thanks @JonnyWong.
* Graph page remembers last selected options. Thanks @JonnyWong.
* New Popular movie homepage stats. Thanks @JonnyWong.
* Add option for duration vs play count on home stats. (Settings -> Extra Settings). Thanks @JonnyWong.
* Clean up media info pages. Don't show metadata that is missing. Thanks @JonnyWong.
* Add clear button to search inputs. Thanks @JonnyWong.
* New columns on Users list. Thanks @JonnyWong.
* New stream duration option for custom notification messages. Thanks @JonnyWong.
* Rad new tooltips on the history pages. Thanks @JonnyWong.
* And a lot of small visual changes and fixes. Thanks @JonnyWong.
* Fixed IP address modal on user history page.
* Fixed "invalid date" showing on monthly plays graph.

## v1.1.2 (2015-08-16)

* Fix bug where user refresh would fail under certain circumstances.

## v1.1.1 (2015-08-15)

* Added Most watched movie for home stats. Thanks @jroyal.
* Added TV show title to recently added text. Thanks @jroyal.
* Fix bug with buffer warnings where notification would trigger continuously after first trigger.
* Fix bug where custom avatar URL would get reset on every user refresh.

## v1.1.0 (2015-08-15)

* Add option to disable all history logging per user.
* Add option to change user avatar URL. Thanks @jroyal.
* Show all users on users table even if they don't yet have history.
* Add option to change time frame of statistics on home page (Settings -> Extra Settings). Thanks @jroyal.
* Add 7 day period for graphs. Thanks @jroyal.
* Add pause, resume and buffer warning notification options.
* Add fine tuning settings for buffer warning triggers.
* Fix issue with SSL cert verification bypass when method doesn't exist (depends on Python version).
* Fix bug on home stats which wouldn't update unless a TV show was first logged.
* Fix alignment of bands on daily graphs which highlight weekends.
* Fix behaviour of close button on update popup, will now stay closed for an hour after clicking close.
* Fix some styling niggles.

## v1.0.1 (2015-08-13)

* Allow SSL certificate check override for certain systems with bad CA stores.
* Fix typo on graphs page causing date selection to break on Safari.

## v1.0 (2015-08-11)

* First release