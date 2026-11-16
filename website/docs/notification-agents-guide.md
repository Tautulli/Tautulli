---
title: Notification Agents Guide
sidebar_position: 7
---

## Browser

1. Click on `Allow Notifications` and give permission for Tautulli to send notifications through your browser.

## Boxcar

**Note:** The Boxcar service has shut down.

1. Go to the Settings page in your Boxcar app.
1. Copy the **Access Token** and fill in the Tautulli setting.

## Discord

1. Go to Discord, and click on **Edit Channel** for the channel where you want the notifications to be sent.
1. Go to the **Integrations** tab and click on **Create Webhook**.
1. Give your webhook bot a **Name** and **Icon**. This can be changed in the Tautulli settings instead if you wish.
1. Copy the **Webhook URL** and fill in the Tautulli setting.

## Email

* **Note:** Some anti-virus software have "Email protection" which may prevent sending emails via SMTP from a script. This will either need to be disabled or add an exception for Tautulli to send emails.

### Gmail

* **Note:** All Google accounts require an [app specific password](https://myaccount.google.com/apppasswords).

```
SMTP Server:     smtp.gmail.com
SMTP Port:       587 or 465
SMTP Username:   YourEmail@gmail.com or Username
SMTP Password:   Your Google app password
Encryption:      TLS/STARTTLS (587) or SSL/TLS (465)
```

### Outlook.com

* **Note:** Outlook.com turned off username and password sign-in for email apps on September 16, 2024. The Tautulli Email agent signs in with a username and password, so it cannot send email through Outlook.com.

## Facebook

Facebook has blocked all non-approved applications from posting to a group programmatically. Although Tautulli shouldn't be against their terms, they are refusing to approve any app that can do this.

Facebook removed the Groups API in April 2024. Tautulli and Zapier can no longer post to a Facebook group.

<details>
<summary>Old, non-working instructions</summary>

[This script](https://gist.github.com/spuniun/56624e1464c621c91e52f88e03321582) by [@spuniun](https://github.com/spuniun) could be used to post directly, however, Facebook has started banning accounts using it so it has been removed from the recommended methods. See the [Custom Scripts](./custom-scripts.md) page for help setting it up.

**Note:** Facebook has [redone their app approval process](https://developers.facebook.com/blog/post/2018/05/01/enhanced-developer-app-review-and-graph-api-3.0-now-live/), as such **all** apps _must_ go through the approval process fully before they will work again. To work around this you can send notifications via email to the group's secret email address from an account that is in the group.

**Note:** As of March 2018, all new Facebook apps require HTTPS for authorization. If Tautulli is not running with HTTPS, the easiest method would be to check "Enable HTTPS" under the Web Interface tab (show advanced). This can be disabled after authorizing with Facebook.

1. Go to [Facebook Developers](https://developers.facebook.com/apps) and click `Add a New App`.
1. Click Add Product on the left, then click `Set Up` for Facebook Login.
1. Skip the Quickstart and go to Facebook Login > Settings on the left, and fill in the **Valid OAuth redirect URIs** with the one provided by Tautulli.
1. Go to Settings > Basic on the left, and fill in a **Privacy Policy URL**.
1. On the same page, get your **App ID** and **App Secret** and fill in the respective Tautulli settings.
1. Go to App Review on the left, and toggle your app to toggle "Make Public" to `Yes`.
1. Click the `Request Authorization` button in Tautulli to allow it to access your Facebook account. Make sure the app visibility is set to `Public` or `Friends` (`Only Me` will not work).
1. Copy the **Access Token** and fill in the Tautulli setting if it is not filled in automatically.
1. Get your **Group ID** from the URL of your group page (e.g. `https://www.facebook.com/groups/<GROUP_ID>`) and fill in the Tautulli setting. If you have customized the URL and no longer have easy access to the Group ID, see [this answer](https://stackoverflow.com/questions/8957340/how-do-i-find-my-facebook-group-id) for how to obtain it. _Note:_ You should _only_ put the ID in the setting for Tautulli, not the full URL.
</details>

## Gotify

1. Go to your Gotify server and click **Apps** at the top.
1. Click `Create Application`.
1. Give your application a **Name** and click `Create`.
1. Copy the **App Token** and fill in the Tautulli setting.

## GroupMe

1. Go to [GroupMe Developers](https://dev.groupme.com) and click **Access Token** at the top. Copy the token and fill in the Tautulli setting.
1. Go to the **Bots** tab at the top and click **Create Bot**.
1. Select the group chat where you want the notifications to be sent, give your bot a **Name** and **Avatar**, and click `Submit`. All other fields can be left at their default values.
1. Copy the **Bot ID** and fill in the Tautulli setting.

## Growl

**Note:** Growl was retired in 2020 and is no longer developed.

1. Open Growl and go to the General tab to make sure Growl is turned `On` and running.
1. Optional: Go to the Security tab to set up a **Password**. Check "Allow network notifications" if Growl is running on a separate machine than Tautulli.
1. Fill in the **Host** for the machine running Growl (e.g. `localhost` or `192.168.0.100`) in the Tautulli settings.
1. Fill in the **Password**, if required, in the Tautulli settings.

## IFTTT

**Note:** The IFTTT Webhooks service requires a paid IFTTT plan.

1. Go to IFTTT and set up your [Webhooks](https://ifttt.com/maker_webhooks) service.
1. Click on **Documentation** to get your **Webhook Key** and fill in the Tautulli setting.
1. Create a [New Applet](https://ifttt.com/create), with "this" as "Webhooks", and the trigger "Receive a web request".
1. Fill in the **Event Name** with the one that matches the Tautulli setting.
      * **Tip:** You can create different IFTTT events (e.g. `tautulli_play`, `tautulli_stop`, `tautulli_created`, etc.) by adding `{action}` to the Event Name in Tautulli (e.g. `tautulli_{action}`).
1. Select "that" as whichever service you want.
1. Fill in the settings of your service by adding the ingredients `Value1`, `Value2`, and `Value3`.
      * `Value1` will be the subject line in your notification text settings.
      * `Value2` will be the body text in your notification text settings.
      * (Optional) `Value3` can be anything you select (e.g. Poster URL).

## Join

1. Go to [Join App](https://joinjoaomgcd.appspot.com), and click on `Join API`, then `Show`.
1. Copy the **API Key** and fill in the Tautulli setting.

## Kodi

1. From within Kodi, go to Settings > Service settings > Control, and make sure "Allow remote control via HTTP" is checked.
1. Optional: Set the **Port**, **Username**, and **Password** for the Kodi Webserver. The default port is `8080`. A username and password are required if "Require authentication" is enabled.
1. Enter in the **Host Address** for the machine running Kodi (e.g. `http://localhost:8080`) in the Tautulli settings.
1. Fill in the **Username** and **Password**, if required, in the Tautulli settings.

## LunaSea

**Note:** LunaSea has shut down, and its notification service is offline.

1. In the LunaSea app, go to Settings > Notifications.
1. Copy the user-based or device-based webhook URL from the Tautulli card and fill in the **LunaSea Webhook URL** Tautulli setting.
1. Fill in the **LunaSea Profile** if you are not using the default LunaSea profile.

## macOS Notification Center

**Note:** macOS Notification Center notifications will only work on the machine where Tautulli is installed.

1. Fill in the path to your Tautulli application. The default is `/Applications/Tautulli`.
1. Click the `Register App` button to register Tautulli with the Notification Center.

## Microsoft Teams

1. In Teams, open **Workflows** and search for the **Send webhook alerts to a channel** template.
1. Select the team and channel where you want the notifications to be sent, and click `Save`.
1. Copy the **Webhook URL** from the workflow details page and fill in the Tautulli setting.

## MQTT

1. Fill in the settings from your MQTT broker.

## ntfy

1. Fill in the **Host Address** of your ntfy server (e.g. `https://ntfy.sh`) in the Tautulli settings.
1. Fill in the **Topic** where you want the notifications to be sent.
1. Optional: If your topic requires a login, create an access token in the Account section of the ntfy web app. Copy the **Access Token** and fill in the Tautulli setting.

## Plex Home Theater

**Note:** Plex Home Theater notifications only work with [OpenPHT](https://forums.plex.tv/t/release-openpht-1-8-0/185459) or [RasPlex](https://forums.plex.tv/t/release-rasplex-1-8-0/185458).

1. From within OpenPHT/RasPlex, go to Preferences > System > Services, and make sure "Allow remote control via HTTP" is checked.
1. Enter in the **Host Address** for the machine running OpenPHT or RasPlex with the port `3005` (e.g. `http://localhost:3005`).
1. Fill in the **Username** and **Password**, if required, in the Tautulli settings.

## Plex Android / iOS App

**Note:** Plex Pass is required to send notifications to the Plex mobile apps.

1. Open the Plex Android or iOS app, go to Settings > Notifications and enable the following notifications matching the triggers in the Tautulli notification agent:
    1. **New Content Added to Library** - Tautulli trigger: Recently Added
        * Note: Make sure to *uncheck* all libraries for the server connected to Tautulli.
    1. **Playback Started** - Tautulli trigger: Playback Start
        * Note: Make sure to *uncheck* the server and all users connected to Tautulli.
    1. **New Devices** - Tautulli trigger: User New Device
        * Note: Make sure to *uncheck* the server connected to Tautulli.
1. Send a Test Notification from Tautulli and you should receive one test notification *for each notification* you have enabled in the Plex App.

**Note:** The user(s) receiving the notifications must have notifications enabled for the matching Tautulli triggers in their Plex mobile app.

**Note:** The user(s) must *uncheck* all the servers, libraries, and users connected to Tautulli in the Plex mobile app settings otherwise they may receive duplicate notifications from Plex and Tautulli. Use the [custom notification agent conditions](./custom-notification-conditions.md) in Tautulli to filter the notifications instead.

**Note:** Push notifications do not need to be enabled in your Plex server Settings > General page. However, you may leave it enabled to receive the other notifications types from Plex (new server shared with you, new item on deck, database corruption detected, database backed up, etc.).

## Prowl

1. Go to [Prowl](https://www.prowl.app/settings/sources), and create a new **API Key** source.
1. Copy the **API Key** and fill in the Tautulli Setting.

## Pushbullet

1. Go to [Pushbullet Account Settings](https://www.pushbullet.com/#settings/account), and click `Create Access Token`.
1. Copy the **Access Token** and fill in the Tautulli Setting.

## Pushover

1. Go to Pushover, and [Create a New Application](https://pushover.net/apps/build).
1. Give your application a **Name** and **Icon**, and click `Create Application`.
1. Copy the **API Token** and fill in the Tautulli Setting.
1. Go back to the [Pushover homepage](https://pushover.net).
      * If you want to send notifications to yourself, copy your **User Key** and fill in the Tautulli setting.
      * If you want to send notifications to a group, go to [Create a New Group](https://pushover.net/groups/build). Copy the **Group Key** and fill in the Tautulli setting.

## Script

* Please see the [Custom Scripts](./custom-scripts.md) page.

## Slack

1. Go to Slack, and create a new [Incoming Webhook](https://my.slack.com/services/new/incoming-webhook).
1. Select the slack channel where you want the notifications to be sent, and click `Add Incoming Webhooks` integration.
1. Copy your **Webhook URL** and fill in the Tautulli setting.
1. Scroll down to Integration Settings, and give your integration a **Name** and **Icon**. This can be changed in the Tautulli settings instead if you wish.

## Tautulli Remote App

* Please see the [Tautulli Remote Wiki](https://github.com/Tautulli/Tautulli-Remote/wiki/Registering-a-Tautulli-server) on how to register your Tautulli Remote [Android](https://play.google.com/store/apps/details?id=com.tautulli.tautulli_remote) or [iOS](https://apps.apple.com/us/app/tautulli-remote/id1570909086?platform=iphone) app.

## Telegram

1. Message [`@BotFather`](https://telegram.me/BotFather) on Telegram with the command `/newbot` to create a new bot.
1. Follow the instructions to give your bot a display name and a bot username.
1. Copy the **Bot Token** and fill in the Tautulli setting.

**Sending Messages to Yourself**

1. Create a new chat with your bot.
1. Message [`@myidbot`](https://telegram.me/myidbot) on Telegram with the command `/getid` to get your **Chat ID**.
1. Copy the **Chat ID** and fill in the Tautulli setting.

**Sending Messages to a Group**

1. Create a new group chat with your bot _in the group_ and [`@myidbot`](https://telegram.me/myidbot).
1. Message [`@myidbot`](https://telegram.me/myidbot) in the group with the command `/getgroupid` to get your **Group ID**.
1. Copy the **Group ID** and fill in the Tautulli setting. Don't forget the hyphen (`-`) in the Group ID.
    *  For a group topic, append `/topicID` to the group ID (e.g. `-1000000000000/2`).

**Sending Messages to a Channel**

**_Public Channel_**

1. Create a new Public Channel in Telegram.
2. Fill in the Public Link to your channel. This is your channel username (e.g. `t.me/<CHANNEL_USERNAME>`).
3. Go to Manage Channel and add your bot to the Administrators.
4. Copy the **Channel Username** and fill in the Tautulli setting. Don't forget the `@` sign (`@<CHANNEL_USERNAME>`) in the Channel Username.

**_Private Channel_**

1. Create a new Private Channel in Telegram.
1. Go to Manage Channel and add your bot and [`@myidbot`](https://telegram.me/myidbot) to the Administrators.
1. Message [`@myidbot`](https://telegram.me/myidbot) in the channel with the command `/getgroupid` to get your **Channel ID**.
1. Copy the **Channel ID** and fill in the Tautulli setting. Don't forget the hyphen (`-`) in the Channel ID.

## Twitter

**Note:** The X (formerly Twitter) API has no free tier. Posting requires purchased X API credits.

1. Go to the [X Developer Console](https://console.x.com) and click `Create App`.
1. Give your app a **Name**, **Description**, and **Use case**.
1. Set the app permissions to `Read and write`.
1. Get your **API Key** and **API Secret**, and fill in the **Consumer Key** and **Consumer Secret** Tautulli settings.
1. Generate your **Access Token** and **Access Token Secret**, and fill in the respective Tautulli settings.

## Webhook

1. Find the **Webhook URL** for the service you are going to be using and fill in the Tautulli setting. Some examples:
    * Discord: [Intro to Webhooks](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
    * Slack: [Incoming Webhooks](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/)
1. Pick the appropriate HTTP request method for your **Webhook Method**. Generally, you want to select `POST` here.
1. Customize the raw **JSON Data** sent to the webhook on the **Data** tab.

<details>
<summary>JSON Data Examples:</summary>

* [ntfy](https://github.com/Tautulli/Tautulli/issues/2160#issuecomment-1741240302)

</details>

## Zapier

**Note:** Webhooks by Zapier is a premium Zapier app and requires a paid Zapier plan.

1. Go to Zapier and [`Make a Zap`](https://zapier.com/editor).
1. For "When this happens...", Choose App as "Webhooks by Zapier", and Choose Trigger as "Catch Hook", then click `Continue`.
1. Copy the **Custom Webhook URL** and fill in the Tautulli setting, then click `Continue` in Zapier.
1. Click `Test & Review` in Zapier, then click the `Send Test Data` button in Tautulli. A new hook will show up in Zapier with test data from Tautulli. Once everything is okay, click `Done Editing`.
1. For "Do this...", Choose App as whichever service you want, and follow the instructions to connect the service.
1. Set Up Template using the values `Body`, `Subject`, `Action`, `Provider Name`, `Provider Link`, `Plex URL`, and `Poster URL`. These values will all be filled in by Tautulli.
1. Make sure your Zap is turned `on` in the top right.
