# Changelog

## v1.0 (2015-08-11)

* First release

## v1.0.1 (2015-08-13)

* Allow SSL certificate check override for certain systems with bad CA stores.
* Fix typo on graphs page causing date selection to break on Safari.

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

## v1.1.1 (2015-08-15)

* Added Most watched movie for home stats. Thanks @jroyal.
* Added TV show title to recently added text. Thanks @jroyal.
* Fix bug with buffer warnings where notification would trigger continuously after first trigger.
* Fix bug where custom avatar URL would get reset on every user refresh.

## v1.1.2 (2015-08-16)

* Fix bug where user refresh would fail under certain circumstances.