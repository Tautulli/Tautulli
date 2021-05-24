### Notification Agents:

* [Boxcar](#boxcar)
* [Browser](#browser)
* [Discord](#discord)
* [Email](#email)
* [Facebook](#facebook)
* [GroupMe](#groupme)
* [Growl](#growl)
* [Hipchat](#hipchat)
* [IFTTT](#ifttt)
* [Join](#join)
* [Kodi](#xbmc)
* [macOS Notification Center](#osx)
* [MQTT](#mqtt)
* [Notify My Android](#nma)
* [Plex Home Theater](#plex)
* [Plex Android / iOS App](#plexmobileapp)
* [Prowl](#prowl)
* [Pushbullet](#pushbullet)
* [Pushover](#pushover)
* [Script](#scripts)
* [Slack](#slack)
* [Tautulli Remote Android App](#androidapp)
* [Telegram](#telegram)
* [Twitter](#twitter)
* [Webhook](#webhook)
* [Zapier](#zapier)

---

### <a id="browser">Browser</a>

1. Click on `Allow Notifications` and give permission for Tautulli to send notifications through your browser.

---

### <a id="boxcar">Boxcar</a>

1. Go to the Settings page in your Boxcar app.
1. Copy the **Access Token** and fill in the Tautulli setting.

---

### <a id="discord">Discord</a>

1. Go to Discord, and click on **Edit Channel** for the channel where you want the notifications to be sent.
1. Go to the **Webhooks** tab and click on **Create Webhook**.
1. Give your webhook bot a **Name** and **Icon**. This can be changed in the Tautulli settings instead if you wish.
1. Copy the **Webhook URL** and fill in the Tautulli setting.

---

### <a id="email">Email</a>

* **Note:** Some anti-virus software have "Email protection" which may prevent sending emails via SMTP from a script. This will either need to be disabled or add an exception for Tautulli to send emails.

#### Gmail

* **Note:** If you use 2-factor authentication, then you will need to generate an app password [here](https://security.google.com/settings/security/apppasswords).
* **Note:** If you don't use 2-factor authentication, you may need to allow less secure apps to access your account. See Option 2 [here](https://support.google.com/accounts/answer/6010255?hl=en&ref_topic=2401957).

```
SMTP Server:     smtp.gmail.com
SMTP Port:       587 or 465
SMTP User:       YourEmail@gmail.com or Username
SMTP Password:   Your Gmail password or app password
Encryption:      TLS/STARTTLS (587) or SSL/TLS (465)
```

#### Outlook.com

* **Note:** If you use 2-factor authentication, then you will need to generate an app password [here](https://account.live.com/proofs/AppPassword).

```
SMTP Server:     smtp.office365.com
SMTP Port:       587
SMTP User:       YourEmail@outlook.com
SMTP Password:   Your Outlook password or app password
Encryption:      TLS/STARTTLS (587)
```

---

### <a id="facebook">Facebook</a>

Facebook has blocked all non-approved applications from posting to a group programmatically. Although Tautulli shouldn't be against their terms, they are refusing to approve any app that can do this.

There only currently known workaround is that Zapier also allows posting to Facebook, see [their agent guide](Notification-Agents-Guide#zapier) for how to set this up. See [here](https://i.imgur.com/rcWtoZk.png) for an example Facebook configuration within Zapier.

<details>
<summary>Old, non-working instructions</summary>

[This script](https://gist.github.com/spuniun/56624e1464c621c91e52f88e03321582) by [@spuniun](https://github.com/spuniun) could be used to post directly, however, Facebook has started banning accounts using it so it has been removed from the recommended methods. See the [Custom Scripts](Custom-Scripts) page for help setting it up.

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

---

### <a id="groupme">GroupMe</a>

1. Go to [GroupMe Developers](https://dev.groupme.com) and click **Access Token** at the top. Copy the token and fill in the Tautulli setting.
1. Go to the **Bots** tab at the top and click **Create Bot**.
1. Select the group chat where you want the notifications to be sent, give your bot a **Name** and **Avatar**, and click `Submit`. All other fields can be left at their default values.
1. Copy the **Bot ID** and fill in the Tautulli setting.

---

### <a id="growl">Growl</a>

1. Open Growl and go to the General tab to make sure Growl is turned `On` and running.
1. Optional: Go to the Security tab to set up a **Password**. Check "Allow network notifications" if Growl is running on a separate machine than Tautulli.
1. Fill in the **Host** for the machine running Growl (e.g. `localhost` or `192.168.0.100`) in the Tautulli settings.
1. Fill in the **Password**, if required, in the Tautulli settings.

---

### <a id="hipchat">Hipchat</a>

1. Go to [Hipchat Integrations](https://www.hipchat.com/addons/), select the room where you want the notifications to be sent, and click **Build your own integration**.
1. Give your integration a **Name** and click `Create`.
1. Copy the **Integration URL** and fill in the Tautulli setting.

---

### <a id="ifttt">IFTTT</a>

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

---

### <a id="join">Join</a>

1. Go to [Join App](https://joinjoaomgcd.appspot.com), and click on `Join API`, then `Show`.
1. Copy the **API Key** and fill in the Tautulli setting.

---

### <a id="xbmc">Kodi</a>

1. From within Kodi, go to Settings > Service settings > Control, and make sure "Allow remote control via HTTP" is checked.
1. Optional: Set the **Port**, **Username**, and **Password** for the Kodi Webserver. The default port is `8080`.
1. Enter in the **Host Address** for the machine running Kodi (e.g. `http://localhost:8080`) in the Tautulli settings.
1. Fill in the **Username** and **Password**, if required, in the Tautulli settings.

---

### <a id="osx">macOS Notification Center</a>

**Note:** macOS Notification Center notifications will only work on the machine where Tautulli is installed.

1. Fill in the path to your Tautulli application. The default is `/Applications/Tautulli`.
1. Click the `Register App` button to register Tautulli with the Notification Center.

---

### <a id="mqtt">MQTT</a>

1. Fill in the settings from your MQTT broker.

---

### <a id="nma">Notify My Android</a>

1. Go to [Notify My Android](https://notifymyandroid.appspot.com/account.jsp) and click `Generate New Key`.
2. Copy the **API Key** and fill in the Tautulli setting.

---

### <a id="plex">Plex Home Theater</a>

**Note:** Plex Home Theater notifications only work with [OpenPHT](https://forums.plex.tv/discussion/264209/release-openpht-1-8-0/p1) or [RasPlex](https://forums.plex.tv/discussion/264208/release-rasplex-1-8-0/p1).

1. From within OpenPHT/RasPlex, go to Preferences > System > Services, and make sure "Allow remote control via HTTP" is checked.
1. Enter in the **Host Address** for the machine running OpenPHT or RasPlex with the port `3005` (e.g. `http://localhost:3005`).
1. Fill in the **Username** and **Password**, if required, in the Tautulli settings.

---

### <a id="plexmobileapp">Plex Android / iOS App</a>

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

**Note:** The user(s) must *uncheck* all the servers, libraries, and users connected to Tautulli in the Plex mobile app settings otherwise they may receive duplicate notifications from Plex and Tautulli. Use the [custom notification agent conditions](Custom-Notification-Conditions) in Tautulli to filter the notifications instead.

**Note:** Push notifications do not need to be enabled in your Plex server Settings > General page. However, you may leave it enabled to receive the other notifications types from Plex (new server shared with you, new item on deck, database corruption detected, database backed up, etc.).

---

### <a id="prowl">Prowl</a>

1. Go to [Prowl](https://www.prowlapp.com/api_settings.php), and generate a new API key by clicking `Generate Key`.
1. Copy the **API Key** and fill in the Tautulli Setting.

---

### <a id="pushbullet">Pushbullet</a>

1. Go to [Pushbullet Account Settings](https://www.pushbullet.com/#settings/account), and click `Create Access Token`.
1. Copy the **Access Token** and fill in the Tautulli Setting.

---

### <a id="pushover">Pushover</a>

1. Go to Pushover, and [Create a New Application](https://pushover.net/apps/build).
1. Give your application a **Name** and **Icon**, and click `Create Application`.
1. Copy the **API Token** and fill in the Tautulli Setting.
1. Go back to the [Pushover homepage](https://pushover.net).
      * If you want to send notifications to yourself, copy your **User Key** and fill in the Tautulli setting.
      * If you want to send notifications to a group, go to [Create a New Group](https://pushover.net/groups/build). Copy the **Group Key** and fill in the Tautulli setting.

---

### <a id="scripts">Script</a>

* Please see the [[Custom Scripts Wiki Page|Custom Scripts]].

---

### <a id="slack">Slack</a>

1. Go to Slack, and create a new [Incoming Webhook](https://my.slack.com/services/new/incoming-webhook).
1. Select the slack channel where you want the notifications to be sent, and click `Add Incoming Webhooks integration.
1. Copy your **Webhook URL** and fill in the Tautulli setting.
1. Scroll down to Integration Settings, and give your integration a **Name** and **Icon**. This can be changed in the Tautulli settings instead if you wish.

---

### <a id="androidapp">Tautulli Remote Android App</a>

* Please see the [Tautulli Remote Wiki](https://github.com/Tautulli/Tautulli-Remote/wiki/Registering-a-Tautulli-server) on how to register your [Tautulli Remote Android App](https://play.google.com/store/apps/details?id=com.tautulli.tautulli_remote).

---

### <a id="telegram">Telegram</a>

1. Message [`@BotFather`](https://telegram.me/BotFather) on Telegram with the command `/newbot` to create a new bot.
1. Follow the instructions to give your bot a display name and a bot username.
1. Copy the **Bot Token** and fill in the Tautulli setting.

**Sending Messages to Yourself**

1. Create a new chat with your bot.
1. Message [`@IDBot`](https://telegram.me/myidbot) on Telegram with the command `/getid` to get your **Chat ID**.
1. Copy the **Chat ID** and fill in the Tautulli setting.

**Sending Messages to a Group**

1. Create a new group chat with your bot and [`@IDBot`](https://telegram.me/myidbot).
1. Message [`@IDBot`](https://telegram.me/myidbot) in the group with the command `/getgroupid` to get your **Group ID**.
1. Copy the **Group ID** and fill in the Tautulli setting. Don't forget the hyphen (`-`) in the Group ID.

**Sending Messages to a Channel**

1. Create a new Public Channel in Telegram.
1. Go to Manage Channel and add your bot to the Administrators.
1. Add a "Link" to your channel. This is your channel username (e.g. `t.me/<CHANNEL_USERNAME>`).
1. Copy the **Channel Username** and fill in the Tautulli setting. Don't forget the at sign (`@<CHANNEL_USERNAME>`) in the Channel Username.

---

### <a id="twitter">Twitter</a>

1. Go to [Twitter Apps](https://apps.twitter.com) and click `Create New App`.
1. Give your app a **Name**, **Description**, and **Website**. A valid website is not required.
1. Go to the "Keys and Access Tokens" tab to get your **Consumer Key** and **Consumer Secret**, and fill in the respective Tautulli settings.
1. Click on `Create my access token` to get your **Access Token** and **Access Token Secret**, and fill in the respective Tautulli settings.

---

### <a id="webhook">Webhook</a>

1. Find the **Webhook URL** for the service you are going to be using and fill in the Tautulli setting. Some examples:
    * Discord: [Intro to Webhooks](https://support.discordapp.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
    * Slack: [Incoming Webhooks](https://api.slack.com/incoming-webhooks)
1. Pick the appropriate HTTP request method for your **Webhook Method**. Generally, you want to select `POST` here.
1. Customize the raw **JSON Data** sent to the webhook on the **Data** tab.

---

### <a id="zapier">Zapier</a>

1. Go to Zapier and [`Make a Zap`](https://zapier.com/app/editor).
1. For "When this happens...", Choose App as "Webhooks by Zapier", and Choose Trigger as "Catch Hook", then click `Continue`.
1. Copy the **Custom Webhook URL** and fill in the Tautulli setting, then click `Continue` in Zapier.
1. Click `Test & Review` in Zapier, then click the `Send Test Data` button in Tautulli. A new hook will show up in Zapier with test data from Tautulli. Once everything is okay, click `Done Editing`.
1. For "Do this...", Choose App as whichever service you want, and follow the instructions to connect the service.
1. Set Up Template using the values `Body`, `Subject`, `Action`, `Provider Name`, `Provider Link`, `Plex URL`, and `Poster URL`. These values will all be filled in by Tatutulli.
1. Make sure your Zap is turned `on` in the top right.
