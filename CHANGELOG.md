# Changelog

## v1.1.3 (2015-08-22)

* Show human readable version info and this cool changelog in Settings -> General.
* Add a "delete" mode to the history tables. Toggle it to show a delete button next to each history item.
* Two digit season and episode numbers for custom notification messages. Thanks @JohnnyWong.
* New FreeNAS init script. Thanks @JohnnyWong.
* Lots of styling improvements! Thanks @JohnnyWong.
* Graph page remembers last selected options. Thanks @JohnnyWong.
* New Popular movie homepage stats. Thanks @JohnnyWong.
* Add option for duration vs play count on home stats. (Settings -> Extra Settings). Thanks @JohnnyWong.
* Clean up media info pages. Don't show metadata that is missing. Thanks @JohnnyWong.
* Add clear button to search inputs. Thanks @JohnnyWong.
* New columns on Users list. Thanks @JohnnyWong.
* New stream duration option for custom notification messages. Thanks @JohnnyWong.
* Rad new tooltips on the history pages. Thanks @JohnnyWong.
* And a lot of small visual changes and fixes. Thanks @JohnnyWong.
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