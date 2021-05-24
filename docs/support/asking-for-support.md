# Asking for Support

## Before asking for support, make sure you try these things first

* Make sure you have updated to the latest version. 
* ["Have you tried turning it off and on again?"](https://www.youtube.com/watch?v=nn2FB1P_Mn8)
* Analyzing your logs, you just might find the solution yourself!
* **Search** the \[\[Wiki\|Home\]\], 

  \[\[Installation Guides\|Installation\]\], and 

  \[\[FAQs\|Frequently Asked Questions\]\].

* If you have questions, feel free to ask them on [Discord](https://tautulli.com/discord) or [Reddit](https://www.reddit.com/r/Tautulli). Please include a link to your logs. See [How can I share my logs?](asking-for-support.md#how-can-i-share-my-logs) for more details. 

## What should I include when asking for support?

When you contact support saying something like "it doesn't work" leaves little to go on to figure out what is wrong for you. When contacting support try to include information such as the following:

* What did you try to do? When you describe what you did to reach the state you are in we may notice something you did different from the instructions, or something that your unique setup requires in addition. Some examples of what to provide here:
  * What command did you enter?
  * What did you click on?
  * What settings did you change?
  * Provide a step-by-step list of what you tried.
* What do you see? We cannot see your screen so some of the following is necessary for us to know what is going on:
  * Did something happen?
  * Did something not happen?
  * Are there any error messages showing?
  * Screenshots can help us see what you are seeing
  * The Tautulli logs show exactly what happened and are often critical for identifying issues \(see [How can I share my logs?](asking-for-support.md#how-can-i-share-my-logs) below\).

When you only provide something like "it doesn't work" think of it like going to the doctor and only telling them "I'm sick." Without you telling them things like what symptoms are you experiencing, whether you are feeling pain somewhere, or whether you are taking any medication. Just like the doctor in that situation, if you don't tell us what is wrong we have to ask you questions until we can get the basic information in place so we can start figuring out how to help you fix the issue.

## How can I share my logs?

First you will need to download your logs by opening the web interface.

1. Go to the **Settings menu** \(Gear Icon, top right\) and click **View Logs**.
2. Click the Download Logs button on the _Tautulli Logs_ tab to save a copy of the `tautulli.log` file.
3. Open the log file and **upload the text** by going to [gist.github.com](https://gist.github.com/) and creating a new secret Gist of the contents.
4. **Share the link** with support \([Discord](https://tautulli.com/discord), [Reddit](https://www.reddit.com/r/Tautulli)\) by copying the URL of the page.

If Tautulli is unable to start, then the log file is located in the following locations:

* Git or zip based installation: `<Tautulli-install-directory>/logs/tautulli.log`
* Windows exe installation: `%LOCALAPPDATA%\Tautulli\logs\tautulli.log`
* macOS pkg installation: `~/Library/Application Support/Tautulli/logs/tautulli.log`
* Snap package installation: `/root/snap/tautulli/common/logs/tautulli.log`

### Notes:

* Upload the **entire** log file. Only uploading what you think is important just makes the process of figuring out what is wrong take longer.
* Not seeing any errors is just as useful as seeing errors. It could indicate that something _isn't_ happening, that should be happening.
* Do not clear your logs unless asked to.
* _Notification Logs_ and _Newsletter Logs_ provide no information for support. These logs are only used to keep a history of what has been sent.

## What is in my logs?

### Tautulli Logs

_Filename: `tautulli.log`_

Tautulli already sanitizes tokens from this log, leaving the following potentially sensitive information in there:

* Usernames
  * Especially if your users leave them as email addresses
* Media titles
  * For example `Session 771 started by user 18140375 (username) with ratingKey 364356 (Solo: A Star Wars Story).`
* Times that things were played

If you want to keep this private feel free to replace the usernames before uploading the logs as long as you do so consistently! For example replacing `alice` with `user1` and `bob` with `user2` is fine, but don't replace one instance of `alice` with `user1`, and another with `user2` or replacing both `alice` and `bob` with `user`.

Information that _isn't_ sensitive:

* Many identifiers aren't sensitive, such as:
  * Session IDs
  * Session keys
  * Rating keys
  * User ID numbers
  * Etc.

These numbers are unique to your specific Plex and Tautulli installation, but have no meaning outside of them so sharing them isn't an issue.

### Tautulli API Logs

_Filename: `tautulli_api.log`_

This log contains information about calls made to Tautulli's own API and is usually not needed for support issues.

### Plex Websocket Logs

_Filename: `plex_websocket.log`_

This is a log of the raw events that Plex sends to Tautulli as your users play media and you add new files. This log shouldn't contain any information more sensitive than the Tautulli Log itself, but is rarely required to diagnose issues.

