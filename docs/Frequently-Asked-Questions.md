**If you can't find a solution here, please ask on [Discord](https://discord.gg/tQcWEUp), [Reddit](https://www.reddit.com/r/Tautulli) or the [Plex Forums](https://forums.plex.tv/discussion/307821/tautulli-monitor-your-plex-media-server). Don't post questions on the GitHub issues tracker.**

## General

* [I am receiving some weird datatable warnings.](#general-q2)
* [I forgot my username and/or password!](#general-q3)
* [I can't reach the web interface!](#general-q4)
* [Tautulli is not updating, it just goes back to the homepage without updating.](#general-q5)
* [When I try to update Tautulli, it keeps telling me "Please commit your changes or stash them before you can merge."](#general-q6)
* [What does the warning "Unable to retrieve data" mean? Is this a problem?](#general-q7)
* [My libraries are duplicated! How do I remove them?](#general-q8)
* [How can I access Tautulli outside my home network?](#general-q9)
* [Why does Tautulli not work with my reverse proxy setup?](#general-q10)
* [I need to move/reinstall Tautulli. Can I keep my history and statistics?](#general-q11)
* [Help! I accidentally deleted a user/library! How can I add it back?](#general-q12)
* [Can I import my history from PlexWatch/Plexivity?](#general-q13)
* [Where can I find my Tautulli logs?](#general-q14)
* [Tautulli says "There was an error communicating with your Plex Server", and the logs say "Status code 401".](#general-q16)
* [I can't connect to my Plex server with "Use SSL" checked.](#general-q17)
* [My Tautulli database got corrupted: "DatabaseError: database disk image is malformed" or "sqlite3.OperationalError".](#general-q18)
* [Tautulli cannot read my Plex log file.](#general-q19)
* [Tautulli won't start due to a corrupted config file.](#general-q20)
* [What data is being collected using Google Analytics?](#general-q21)
* [I'm seeing an "Unable to connect to remote host because of a SSL error." message when trying to update.](#ssl-update)
* [Does Tautulli have to be installed on the same machine as my Plex Server?](#install-same-machine-plex)
* [Recently added items are not showing up on the homepage.](#recently-added-homepage)
* [My users list is not updating and I am seeing "Status code 404" in the logs.](#users-list-not-updating)
* [My media info table is not loading.](#media-info-table-not-loading)

## Activity and History Logging

* [What is the grey progress bar under the current activity?](#history-q2)
* [I can see the streams on the homepage, but nothing is being logged.](#history-q3)
* [Do I need to keep Tautulli running to record history?](#history-q4)
* [Can Tautulli import history from before it was installed?](#history-q5)
* [Watch history isn't showing up under "Recently Watched" on the homepage.](#history-q6)
* [After resuming a media item, it shows up as two plays in Tautulli.](#history-q7)
* [The logs keep telling me "Failed to write sessionKey XX ratingKey YY to the database. Will try again on the next pass."](#history-q8)
* [Can I see which items in my libraries are the *least watched*?](#history-q9)
* [My concurrent streams statistic is showing an insane number!](#history-q10)
* [I am seeing history entries with very long duration times.](#history-q11)
* [Why does the bandwidth show as higher than the quality?](#history-q12)
* [I moved media in Plex, now Tautulli is linking to the wrong item/showing up twice!](#move-media)
* [I'm seeing the same artist twice on the homepage!](#homepage-duplicate-artist)
* [Why are items showing up as 127.0.0.1 for the IP address?](#plex-relay)
* [Can I disable history logging for a specific user/library?](#disable-logging)

## Live TV

* [Why do I suddenly have a "Live TV" library?](#livetv-library)
* [Why don't I see the "Live TV" library?](#livetv-library-missing)
* [I played multiple shows on Live TV but Tautulli says I only watched one show the entire time.](#livetv-rollover)
* [How do I disable history logging for Live TV?](#livetv-disable-logging)
* [Can I view the history for an entire TV show I watched on Live TV similar to TV shows in my own library?](#livetv-show-history)
* [How do I hide Live TV on the Graphs page?](#livetv-hide-graphs)

## Notifications

* [I can't get Notifications working! Is there a magic trick?](#notifications-q1)
* [My tests say they are successful, but the notification isn't sent and there's nothing in the logs.](#notifications-q2)
* [Can I disable notifications for a specific user/library?](#notifications-q3)
* [Can I disable recently added notifications for TV Shows/Movies?](#notifications-q4)
* [All my recently added notifications are showing `S00E01`.](#notifications-q5)
* [Why are posters not showing up in my notifications?](#notifications-q7)
* [How do I set up Imgur for notification posters?](#imgur)
* [Facebook notifications are telling me "Insufficient permission to post to target on behalf of the viewer".](#notifications-q9)
* [Facebook notifications are telling me "Some of the aliases you requested do not exist".](#notifications-q10)
* [I'm seeing a "The PyCryptodome library is missing." message!](#notifications-pycryptodome)
* [Notifications are sending the wrong text/sending the default text.](#notifications-text-ignored)
* [How do I override the Python version in a script?](#notifications-override-python)
* [My recently added notifications are not sending and the logs say "Not notifying again".](#notifications-not-notifying-again)
* [My playback stop notifications are not working.](#stop-notifications)

## Newsletters

* [I enabled a library but it's not showing in the newsletter!](#newsletter-recently-added-library)
* [Gmail is giving me a "Message clipped" message!](#message-clipped)
* [How do I edit the date format?](#newsletter-date-format)
* [Images are not showing up in my newsletter emails.](#newsletter-missing-images)
* [I want to customize the newsletter.](#newsletter-custom-template)

## Windows

* [I enabled HTTPS but received a warning that the pyOpenSSL module is missing. How do I fix this?](#windows-q1)
* [Tautulli keeps telling me "You're running an unknown version of Tautulli."](#windows-q2)
* [When trying to update, the logs say "Invalid update data, update failed."](#windows-q3)
* [I am getting a "DatabaseError: file is encrypted or is not a database"!](#windows-q4)
* [How can I run Tautulli without the command prompt staying open?](#windows-q5)
* [The command prompt just flashes open then closes immediately when starting Tautulli.](#windows-q6)

## OSX

* [When trying to update, the logs say "Agreeing to the Xcode/iOS license requires admin privileges, please re-run as root via sudo."](#osx-q1)
* [I'm getting a `ValueError: unknown locale: UTF-8` message](#osx-unknown-locale)
* [How do I get rid of the Python rocket icon in my dock?](#osx-python-dock)

## QNAP

* [How do I set the Plex Logs Folder on QNAP?](#qnap-q1)

---

### General

#### <a id="general-q2">Q:</a> I am receiving some weird datatable warnings.
**A:** Most datatable warnings can be solved by doing a force refresh in your browser (<kbd>CTRL</kbd>+<kbd>F5</kbd> or <kbd>OPTION</kbd>+<kbd>Reload</kbd> on Mac/Safari). If that doesn't work, try clearing your browser's cache.

#### <a id="general-q3">Q:</a> I forgot my username and/or password!
**A:** Follow these steps to get back in:
1. **Shut down** Tautulli so your changes will apply.
2. Open the Tautulli `config.ini` file with your preferred text editor.
3. Search for `http_username` and `http_password` and the values after the equal signs are the username and password. You can also delete both lines from the file to disable authentication.

_Note: If your password is encrypted in the config file, you will have to delete the entire line to disable authentication and reset your password in the Tautulli settings._

#### <a id="general-q4">Q:</a> I can't reach the web interface!
**A:** Shut down Tautulli and open the Tautulli `config.ini` file with your preferred text editor, search for the lines that begin with `http_host`, `http_port`, and `http_root` and remove the entire line. You should also remove the line for `enable_https` from the file. After you have removed these lines from `config.ini`, go ahead and start Tautulli. It will listen on the default IP address and port (`http://localhost:8181`).

#### <a id="general-q5">Q:</a> Tautulli is not updating, it just goes back to the homepage without updating.
**A:** When you try you Tautulli and you get the message "A newer version (vX.Y.ZZ) is available", but updating doesn't actually update Tautulli there are two ways you can solve the problem, depending on how you installed Tautulli.

##### Git based installation

If you installed Tautulli by cloning the `git` repository, it's possible your local `git` repository has gotten out of sync in a manner that Tautulli can't automatically update from.

If you are running Tautulli v2.2.0 or newer you can have Tautulli attempt to fix this itself by going to Settings -> General -> [Show Advanced] -> Repair Git Install -> Reset. This will attempt to automatically run the commands described below for you, cleaning up some common issues.

If you are running an older version of Tautulli, or the above didn't work, you will need to manually fix this. First **Shutdown Tautulli**, then run the following commands from the command line/shell in the Tautulli folder.
```sh
git remote set-url origin https://github.com/Tautulli/Tautulli.git
git fetch origin
git checkout master
git branch -u origin/master
git reset --hard origin/master
git pull
```

If you are running Tautulli as a dedicated user as is recommended in the [Daemon instructions](Install-as-a-daemon), it's likely the permissions on files will need to be fixed after running the above commands:
```sh
sudo chown -R tautulli:tautulli /path/to/Tautulli
```

##### ZIP install

If you instead installed Tautulli by simply downloading the current release archive, the steps are simpler:
1. Download the [current release](https://github.com/Tautulli/Tautulli/zipball/master)
2. Shut down Tautulli
3. Extract the current release to the same location where you previously extracted it
    * Note: You should be _replacing_ the existing files, if you are prompted about this please select to replace the files!
4. If needed, ensure the permissions are correct
    * For example: `sudo chown -R tautulli:tautulli /path/to/Tautulli`
5. Start Tautulli

#### <a id="general-q6">Q:</a> When I try to update Tautulli, it keeps telling me "Please commit your changes or stash them before you can merge."
**A:** See the answer to the previous question.

#### <a id="general-q7">Q:</a> What does the warning "Unable to retrieve data" mean? Is this a problem?
**A:** No, not necessarily. It means that you requested data that is not available, for example when you view the profile of a user who hasn't watched anything yet or view synced items when there is nothing synced.

#### <a id="general-q8">Q:</a> My libraries are duplicated! How do I remove them?
**A:** This usually happens when you try to reinstall or switch your Plex Media Server. You can visit the following URL to remove all libraries not associated with the current Plex server connected to Tautulli.

```
http://localhost:8181/delete_duplicate_libraries
```

If the libraries are duplicated on the homepage, toggle the Library Statistic cards under Settings > Homepage and click Save.

#### <a id="general-q9">Q:</a> How can I access Tautulli outside my home network?
**A:** **WARNING:** Before you follow any of these methods make sure you have enabled authentication in Tautulli under Settings -> Web Interface by setting a HTTP Username and Password. If you load Tautulli in an Incognito window you should get a login prompt!

The easy and least secure method is to forward an external port (`8181`) on your router to the internal port used by Tautulli (default is TCP `8181`). Visit [Port Forward](http://portforward.com/) for instructions for your particular router. You will then be able to access Tautulli via `http://EXTERNAL-IP-ADDRESS:8181`.

The more advanced and most preferred method (and more secure if you use SSL) is to set up a web server with NGINX/Apache, and use a reverse proxy to access Tautulli. You can lookup many guides on the internet to find out how to do this.

The most secure method, but also the most inconvenient, is to set up a VPN tunnel to your home server, then you can access Tautulli as if it is on a local network via `http://LOCAL-IP-ADDRESS:8181`.

#### <a id="general-q10">Q:</a> Why does Tautulli not work with my reverse proxy setup?
**A:** Tautulli uses CherryPy as it's web server, and it includes support for reverse proxies. You must ensure that your proxy web server (e.g. NGINX or Apache) is sending the standard `X-` headers to CherryPy. For **NGINX**, the configuration would look like this:

```nginx
# Standard proxying headers
proxy_set_header    Host                $host;
proxy_set_header    X-Real-IP           $remote_addr;
proxy_set_header    X-Forwarded-Host    $server_name;
proxy_set_header    X-Forwarded-For     $proxy_add_x_forwarded_for;
```

If you have SSL enabled on your webserver (e.g. `Internet --> https://nginx --> http://tautulli`), make sure HTTP Proxy is checked under Settings > <kbd>Show Advanced</kbd> button > Web Interface. Then ensure that your proxy web server is also including these two SSL specific `X-` headers:

```nginx
# SSL proxying headers
proxy_set_header    X-Forwarded-Proto   $scheme;
proxy_set_header    X-Forwarded-Ssl     on;
```

As an alternative, the following configuration will automatically work for both HTTP and HTTPS.
```nginx
location /tautulli/ {
    proxy_pass http://127.0.0.1:8181;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Host $server_name;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 90;
    proxy_set_header X-Forwarded-Proto $scheme;
    set $xforwardedssl "off";
    if ($scheme = https) {
            set $xforwardedssl "on";
    }
    proxy_set_header X-Forwarded-Ssl $xforwardedssl;
    proxy_redirect ~^(http(?:s)?://)([^:/]+)(?::\d+)?(/.*)?$ $1$2:$server_port$3;
}
```

Don't forget to clear your web browser's cache *every* time you update your web server configuration.

#### <a id="general-q11">Q:</a> I need to move/reinstall Tautulli. Can I keep my history and statistics?
**A:** Yes, all you need to do is download a copy your `tautulli.db` database file and `config.ini` configuration file by clicking on the "Database File" and "Configuration File" links on the Settings > Help & Info page. Then after reinstalling and completing the setup wizard, go to the Settings > Import & Backup page to import the old `tautulli.db` database and `config.ini` configuration files. This will work between any OS.

**WARNING**: If you are re-installing Plex as well please follow [their guide to Move an Install to Another System](https://support.plex.tv/articles/201370363-move-an-install-to-another-system/). If you are starting from scratch again with Plex, or forgot to do this step, then you **MUST** run the script from [this FAQ entry](#move-media), or your Tautulli database will link to the wrong items!

#### <a id="general-q12">Q:</a> Help! I accidentally deleted a user/library! How can I add it back?
**A:** If you have deleted a user or library in Tautulli and would like to bring them back the best method is to immediately restore a backup as the related history for these are removed when they are deleted. If you no longer have a backup containing the history, or don't want to bother with recovering it, you can simply tell Tautulli to allow them back in by "undeleting" them with the following instructions.

##### Undeleting a user
If you are trying to undelete a user first you will need to find their `user_id`. You can get this by following the "More XML Shortcuts" instructions [here](Debugging#more-xml-shortcuts) for "All Users".

You will see a list of items, find the entry that corresponds to the user you want to undelete, the `user_id` is in the `id="12345"` part. So for example in this entry the `user_id` would be `8367478`:
```xml
<User id="8367478" title="exampleuser" username="exampleuser" email="example@domain.com" ...>
    <Server id="1234567" name="Server Name" ... />
</User>
```

Once you have the ID you need to go to `/undelete_user?user_id=<user_id>` on your Tautulli instance. For example for the above ID on a Tautulli instance on the same machine you would go to:
```
http://localhost:8181/undelete_user?user_id=8367478
```

If you are unable to find the `user_id`, you may try using the username (`/undelete_user?username=<username>`) or their email address (`/undelete_user?username=<user's Plex email address>`), but these are less accurate and may not work. Example usage of these for a Tautulli instance running on the same computer would be:
```
http://localhost:8181/undelete_user?username=exampleuser
http://localhost:8181/undelete_user?username=example@domain.com
```

##### Undeleting a library

If you are trying to undelete a library you will need to find the `section_id`. You can get this by following the "More XML Shortcuts" instructions [here](Debugging#more-xml-shortcuts) for "All Libraries".

You will see a list of items, find the entry that corresponds to the library you want to undelete, the `section_id` is in the `key="2"` part. So for example in this entry the `section_id` would be `3`:
```xml
<Directory ... key="3" type="show" title="TV Shows" ...>
    <Location id="7" path="/mnt/TV Shows"/>
</Directory>
```

Once you have the section ID you need to go to `/undelete_library?section_id=<section_id>` on your Tautulli instance. For example for the above ID on a Tautulli instance on the same machine you would go to:
```
http://localhost:8181/undelete_library?section_id=3
```

If you are unable to find the `section_id`, you may try using the library name (`/undelete_library?section_name=<section_name>`), but this is less accurate and may not work. Example usage for a Tautulli instance running on the same computer would be:
```
http://localhost:8181/undelete_library?section_name=Anime
```

#### <a id="general-q13">Q:</a> Can I import my history from PlexWatch/Plexivity?
**A:** You can import your PlexWatch/Plexivity history into Tautulli by going to Settings > Import & Backups.

#### <a id="general-q14">Q:</a> Where can I find my Tautulli logs?
**A:** You can view the Tautulli logs from the web interface by clicking on "View Logs" in the settings menu. Clicking on the "Download logs" button on this page will allow you to save a copy of the log file. The location of the log file is also listed on the Settings > Help & Info page.

If Tautulli is unable to start, then the log file is located in the following locations:
* Git or zip based installation: `<Tautulli-install-directory>/logs/tautulli.log`
* Windows exe installation: `%LOCALAPPDATA%\Tautulli\logs\tautulli.log`
* macOS pkg installations: `~/Library/Application Support/Tautulli/logs/tautulli.log`

When reporting an issue, please provide a link to this log file by pasting it on [Gist](http://gist.github.com), *do not* upload the file as an attachment.

#### <a id="general-q16">Q:</a> Tautulli says "There was an error communicating with your Plex Server", and the logs say "Status code 401".
**A:** Go into the Tautulli Settings > Plex Media Server and fetch a new Plex.tv token.

#### <a id="general-q17">Q:</a> Tautulli can't connect to my Plex server locally with "Use SSL" checked.
**A:** First check that you can access your server locally with SSL. Open your Tautulli settings, go to the Plex Media Server section and copy the "Plex Server URL" URL into a new browser tab to attempt to load your server's interface directly.

If you cannot load the Plex Web interface, then you may have a DNS rebinding issue for `*.plex.direct` addresses. Try changing your system to use a public DNS server, such as [Cloudflare DNS](https://developers.cloudflare.com/1.1.1.1/setting-up-1.1.1.1/) or [Google Public DNS](https://developers.google.com/speed/public-dns/docs/using). If you are using a custom DNS server such as on a pfSense firewall, see the "DNS Rebinding" section of this Plex support article on [How to use Secure Server Connections](https://support.plex.tv/articles/206225077-how-to-use-secure-server-connections/).

Otherwise, you may have to set secure connections to "Preferred" in your Plex server settings and uncheck the "Use SSL" box in the Tautulli settings. Tautulli will then connect to your Plex server directly without SSL using the address `http://LOCAL-IP-ADDRESS:32400`.

#### <a id="general-q18">Q:</a> My Tautulli database got corrupted: "DatabaseError: database disk image is malformed" or "sqlite3.OperationalError".
**A:** There are two ways to fix Tautulli when you get this message:
##### The Easy Way

The easiest way to fix this is to just restore an older version of the database from the backup directory. To do this:

1. Shutdown Tautulli if it is running.
2. Move or rename the current `tautulli.db`.
3. Copy the latest `backups/tautulli.backup-YYYYMMDDHHMMSS.sched.db` file to the main folder as `tautulli.db`.
4. Start Tautulli back up.

##### The Long Way

If restoring a backup won't work for you, or you want to retain as much history from your current database as possible, then the other alternative is to attempt to repair the database that you currently have. If you are using Windows or Mac OS, then you can try the steps below. Alternatively, you can try using the [SQLite command line instructions here](http://froebe.net/blog/2015/05/27/error-sqlite-database-is-malformed-solved/).

1. Backup your Tautulli database (`tautulli.db`) by making a copy and saving it somewhere safe.
2. Open your database with [DB Browser for SQLite](http://sqlitebrowser.org/).
3. Go to "Tools > Integrity Check", then click "OK" to run `PRAGMA pragma integrity_check;` ([screenshot](./images/pragma_integrity_check.png)). If it does not say "ok" then you need to repair your database.
4. Go to "File > Export > Database to SQL file..."
5. Make sure the box that says "Multiple rows (VALUES) per INSERT statement" is checked ([screenshot](./images/multiple_rows_per_insert.png)).
6. Click "OK" and save the `.sql` file on your computer.
7. Go to "File > Close Database".
8. Go to "File > Import > Database from SQL file..."
9. Select the `.sql` file you saved from step 4, and save the new file as `tautulli.db`. Do not overwrite your original file!
    * If you run into an error during the above step see the note below!
10. Save the changes to the database when prompted
10. _(Optional)_ Go to the "Execute SQL" tab and run `pragma integrity_check;` and it should say "ok".
11. Go to "File > Close Database".
12. Replace your Tautulli database (`tautulli.db`) file with this new one.

_Note:_
If you run into issues during step 9 above when building a new database from your exported SQL file the first thing to try would be a minimal export that _only_ saves your history and settings. To do this:
1. Follow the steps above, however during step 5 instead of selecting all tables you will want to change that to only export the following tables:
    * mobile_devices
    * newsletters
    * notifiers
    * session_history
    * session_history_media_info
    * session_history_metadata

2. Continue running through the steps above. If you run into issues again with the minimal table list it's still possible to recover data, but the process is very involved so we ask that you contact [support in Discord](https://tautulli.com/discord) in order to proceed.

#### <a id="general-q19">Q:</a> Tautulli cannot read my Plex log file.
**A:** Tautulli does not require your Plex logs to function. You can add your Plex logs folder to Tautulli in order to use it as a convenient log viewer. If you are installing Tautulli in a Docker container or jail, then you will need to mount/share the Plex log folder into the Tautulli container. You must also specify the full path to the Plex logs folder (shortcuts will not work).

#### <a id="general-q20">Q:</a> Tautulli won't start due to a corrupted config file
**A:** Your `config.ini` file is corrupted. Either delete the file (you will have to reconfigure your Tautulli settings) or try restoring a config file from the backups folder.

#### <a id="general-q21">Q:</a> What data is being collected using Google Analytics?
**A:** Only basic data is being collected, and it is not user identifiable. Here is a sample of the data being collected:

```
Data Source:       server
App Name:          Tautulli
App Version:       v2.0.22
Install Method:    git
Git Branch:        master
Platform:          Windows 10
Language:          en-US
Encoding:          UTF-8
Country:           Canada       # Collected by Google Analytics by default
City:              Vancouver    # Collected by Google Analytics by default
```

If you would like to opt-out of data collection, you can set `system_analytics = 0` in the `config.ini` file. Tautulli must be shut down when editing the file.


#### <a id="ssl-update">Q:</a> I'm seeing an "Unable to connect to remote host because of a SSL error." message when trying to update.
**A:** This is being caused by a combination of several different things. The initial cause is that GitHub has [disabled weak cryptographic standards](https://githubengineering.com/crypto-deprecation-notice/), preventing clients using these standards from accessing their site. This has caused many different aspects of older systems to run into issues when working on updates.

If you are on macOS, first try updating to at least 10.13.4.

The solution to most of these problems is to simply ensure you are on the latest v3 release of [Python](https://www.python.org/downloads/). If that doesn't work for you, the next thing to try is installing the latest version of [`pyOpenSSL`](https://pypi.python.org/pypi/pyOpenSSL), instructions for Windows can be found [here](#windows-q1). That should allow Tautulli to talk to GitHub again and check for updates.

If you are on a `git` based installation and `git` itself runs into problems when trying to download the updates, you should make sure you are on the current version of `git` for your platform.

If after performing all of the above steps have not solved your issue please join the `#support` channel of our [Discord server](https://discord.gg/tQcWEUp) as there can be _many_ platform specific issues related to this.

#### <a id="install-same-machine-plex">Q:</a> Does Tautulli have to be installed on the same machine as my Plex Server?
**A:** No, Tautulli can be installed anywhere as long as it has network access to the Plex server whether that be on a local network or even a remote network.

#### <a id="recently-added-homepage">Q:</a> Recently added items are not showing up on the homepage.
**A:** The recently added section on the homepage is pulled directly from your Plex dashboard. The [Edit Library > Advanced > Include in dashboard](https://i.imgur.com/wiyT30F.png) setting must be enabled for the libraries on your Plex server.

#### <a id="users-list-not-updating">Q:</a> My users list is not updating and I am seeing "Status code 404" in the logs.
**A:** Your Plex Server Identifier in the Tautulli settings is mismatched with your Plex server. Please verify your server in the settings and make sure the identifier matches with the one shown by visiting `http://SERVER-IP:32400/identity`.

#### <a id="media-info-table-not-loading">Q:</a> My media info table is not loading.
**A:** Clear the media info table cache by going to the following URL, where `XX` is the ID number for the library.

```
http://localhost:8181/delete_media_info_cache?section_id=XX
```

---

### Activity and History Logging

#### <a id="history-q2">Q:</a> What is the grey progress bar under the current activity?
**A:** The yellow progress bar is the current stream progress, and the grey bar is the current transcoder progress (not the available buffer on the client device).

#### <a id="history-q3">Q:</a> I can see the streams on the homepage, but nothing is being logged.
**A:** History is only logged if all those following conditions are satisfied:

* After the stream is stopped.
* If the total stream duration is longer than the "Ignore interval" you set (Settings > General > <kbd>Show Advanced</kbd>).
* If "Keep History" for the user is enabled (Users > Edit Mode > Toggle Keep History).
* If "Keep History" for the library is enabled (Libraries > Edit Mode > Toggle History).

If you have satisfied all the above requirements, but nothing is still being logged, then the sessions might be stuck inside the database. Go to Settings > General > <kbd>Show Advanced</kbd> button at the top > Flush Temporary Sessions > Flush to flush the database, and history logging should be working again.

_Note:_ If you are experiencing errors in the log, such as the [`DatabaseError: database disk image is malformed`](#general-q18) error, you should fix those first _before_ attempting to flush sessions above.

#### <a id="history-q4">Q:</a> Do I need to keep Tautulli running to record history?
**A:** Yes. Tautulli cannot "see" your Plex activity if it isn't running, or retroactively import old history.

#### <a id="history-q5">Q:</a> Can Tautulli import history from before it was installed?
**A:** No, unless you had PlexWatch or Plexivity installed previously and import the database, Tautulli can only start logging history after it is installed.

Although Plex _does_ keep some information in their database, it is nowhere near detailed enough to build the level of history that Tautulli keeps, the above tools keep enough information to build partial records from.

#### <a id="history-q6">Q:</a> Watch history isn't showing up under "Recently Watched" on the homepage.
**A:** "Recently Watched" only shows history that is considered as "watched" (exceed the watched percent that you specify in the settings).

#### <a id="history-q7">Q:</a> After resuming a media item, it shows up as two plays in Tautulli.
**A:** Re-Enable "Group Successive Play History" in Settings > General > <kbd>Show Advanced</kbd> button.

#### <a id="history-q8">Q:</a> The logs keep telling me "Failed to write sessionKey XX ratingKey YY to the database. Will try again on the next pass."
**A:** Tautulli can't find your library item `YY`. You can double check if that item exists by using Tautulli and going to

```
http://localhost:8181/info?rating_key=YY
```

If the item can't be found then you can flush the temporary sessions database in Settings > General > <kbd>Show Advanced</kbd> button at the top > Flush Temporary Sessions > Flush.

#### <a id="history-q9">Q:</a> Can I see which items in my libraries are the *least watched*?
**A:** You can find out which items have not been watched by viewing the Media Info table for the library.

#### <a id="history-q10">Q:</a> My concurrent streams statistic is showing an insane number!
**A:** You can try fixing your database by following the steps below:

1. Create a backup of your Tautulli database (`tautulli.db`) by going to Settings > Import & Backups > Backup Database
2. Shutdown Tautulli.
3. Open your database with [DB Browser for SQLite](http://sqlitebrowser.org/).
4. Go to the "Execute SQL" tab and run the following SQL:

        DELETE FROM session_history WHERE id NOT IN (SELECT id FROM session_history_metadata);
        DELETE FROM session_history_media_info WHERE id NOT IN (SELECT id FROM session_history_metadata);

5. Go to "File > Write Changes" and "File > Close Database".
6. Restart Tautulli.

#### <a id="history-q11">Q:</a> I am seeing history entries with very long duration times.
**A:** There's a websocket bug in the recent PMS versions where streams don't send a "stop" event. Once you restart Tautulli, a stop event is triggered, and the duration is calculated from when the stream started to when Tautulli was restarted.

The only solution at the moment is to manually delete those history entries from the History tab.

#### <a id="history-q12">Q:</a> Why does the bandwidth show as higher than the quality?
**A:** The bandwidth shown at the bottom of an activity item is Plex's Streaming Brain _estimate_ of required bandwidth to stream the item. This is not necessarily the same as how much bandwidth will actually be _used_, but instead is the maximum required at the user's chosen bitrate. This can get quite a bit higher than the average bandwidth of the entire item due to the way that video compression works. You can read more detail on the subject and how Plex handles it in the _Bitrates and How They Matter_ section of [this support article](https://support.plex.tv/articles/227715247-server-settings-bandwidth-and-transcoding-limits/).

#### <a id="move-media">Q:</a> I moved media in Plex, now Tautulli is linking to the wrong item/showing up twice!
**A:** When you remove something from Plex and then later re-add it, including when you move it between libraries or recreate an entire library it can start showing up multiple times in Tautulli. This is because Tautulli bases it's history recording on the `ratingKey` provided by Plex, a unique identifier for each item in the library. When you recreate items Plex generates a new `ratingKey` for the new item... but Tautulli is still referencing the old `ratingKey` for the history it has recorded!

_Okay, so how do I fix it?_

This depends on how many items in your history you need to update to their new `ratingKey`. If you've just moved a single movie, or re-added a TV show then the simplest method is to search Tautulli's history for the old item (either the movie, or an episode from the show). Once you've found the item, open up the `/info` page for it and hit the <kbd>Fix Match</kbd> button. This will bring up a screen allowing you to search your Plex library for where the item is currently. Once you find it's new location and tell Tautulli about it, it will update all history items to the new `ratingKey`. For TV shows it will update _all_ episodes, so you just need to fix one.

If you instead recreated an entire library, you might find it easier to setup and use the [update_all_metadata.py](https://gist.github.com/JonnyWong16/f554f407832076919dc6864a78432db2) script, which will automate the above task for everything in your library. Note that you will likely need to manually fix some items using the above method after running this, it will print warnings about the items it was unable to match automatically.

#### <a id="homepage-duplicate-artist">Q:</a> I'm seeing the same artist twice on the homepage!
**A:** This is happening because the lists on the homepage display the _Track_ Artist, but uses the _Album_ Artist for grouping. Plex doesn't provide a linking between track artists and the "real" artist for Tautulli to follow to merge these entries. This means that if you have an artist individually in your library, _and_ they show up in an album of various artists, they will show twice if both are played.

#### <a id="plex-relay">Q:</a> Why are items showing up as 127.0.0.1 for the IP address?
**A:** If a user is unable to get a direct connection to your Plex server for whatever reason, Plex has a component called "Plex Relay" that will relay their traffic through Plex's servers, allowing them to still connect to your server. Unfortunately since they are not connecting directly, the "address" they are connecting from is the local (`127.0.0.1`) connection of the Plex Relay service.

For more information on this, and several potential solutions to fixing the connection issues and enabling direct access to your server, please refer to the [Accessing a Server through Relay](https://support.plex.tv/articles/216766168-accessing-a-server-through-relay/) support article from Plex.

#### <a id="stop-notifications">Q:</a> My playback stop notifications are not working.
**A:** By default Tautulli filters out playback stop notifications after the watched percentage is exceeded. This is to prevent double notifications (both watched and stopped) when a stream finishes. To disable this filtering, allowing all events to always go through, you need to enable the _Notifications & Newsletters -> Show Advanced -> Allow Playback Stop Notifications Exceeding Watched Percent_ setting.

#### <a id="disable-logging">Q:</a> Can I disable history logging for a specific user/library?
**A:** You can control which users/libraries will get logged by going to the Users or Libraries page, going into "Edit mode" and clicking on the "Toggle History" icon beside each user or library you want to enable or disable.

---

### Live TV

#### <a id="livetv-library">Q:</a> Why do I suddenly have a "Live TV" library?
**A:** This "fake" library is used to collect all the Live TV history together. If you don't want to see this then you can go to the Libraries page, click on the "Edit Mode" button, delete the library, and it will not reappear again. If in the future you want to re-enable the library, then you will need to [undelete](#general-q12) the library (`section_id=999999`). Note that, just like any other library, deleting the Live TV library will prevent history from being recorded while it is deleted.

#### <a id="livetv-library-missing">Q:</a> Why don't I see the "Live TV" library?
**A:** The "Live TV" library will only show up the first time you play Live TV in Plex. If you deleted the library, then see the previous answer to add it back.

#### <a id="livetv-rollover">Q:</a> I played multiple shows on Live TV but Tautulli says I only watched one show the entire time.
**A:** This depends on the client you were using to watch Live TV. Some Plex clients (e.g. Plex Web) will update your Plex Media Server's API when Live TV rolls over into the next show. In this case Tautulli will correctly split the history into separate shows. However, some Plex clients (e.g. Apple TV) do not update your Plex Media Server's API so there is no way for Tautulli to know the show changed. Once this is fixed by Plex, it will automatically work correctly in Tautulli.

#### <a id="livetv-disable-logging">Q:</a> How do I disable history logging for Live TV?
**A:** History logging can be disabled like any other library. Go to the Libraries page, click on the "Edit Mode" button, and click on the "Toggle History" icon for the libraries you wish to disable history logging.

#### <a id="livetv-show-history">Q:</a> Can I view the history for an entire TV show I watched on Live TV similar to TV shows in my own library?
**A:** No, this is currently not possible. You can only view history for a single episode at a time on the info pages.

#### <a id="livetv-hide-graphs">Q:</a> How do I hide Live TV on the Graphs page?
**A:** Click on the graph legends to hide the series from the graphs. The graph series visibility is stored in your browser so this will need to be done for each browser that you use.

---

### Notifications

#### <a id="notifications-q1">Q:</a> I can't get Notifications working! Is there a magic trick?
**A:** To be honest: Yes. To be very honest: No. You probably forgot to enable any triggers for your notification agents. If they show with a gray bell in the list then they have no active triggers. Click on the gray bell icon next to the Notification Agent, go to the Triggers tab, and enable any desired triggers for that agent. After you checked at least one trigger and clicked on Save the bell turns satisfying orange-ish.

#### <a id="notifications-q2">Q:</a> My tests say they are successful, but the notification isn't sent and there's nothing in the logs.
**A:** Sometimes the browser cache will cause problems with the test notifications. Do a force refresh on the settings page (<kbd>CTRL</kbd>+<kbd>F5</kbd> or <kbd>OPTION</kbd>+<kbd>Reload</kbd> on Mac/Safari), then try sending a test notification again.

#### <a id="notifications-q3">Q:</a> Can I disable notifications for a specific user/library?
**A:** You can control which users/libraries will send a notification by setting up a [[custom condition|Custom Notification Conditions]] in your notification agent settings.

#### <a id="notifications-q4">Q:</a> Can I disable recently added notifications for TV Shows/Movies?
**A:** See previous answer.

#### <a id="notifications-q5">Q:</a> All my recently added notifications are showing `S00E01`.
**A:** You probably have "Group notifications for recently added TV Shows or Music" checked in the notification settings. No Season/Episode or Album/Track metadata will be available with this setting enabled.

#### <a id="notifications-q7">Q:</a> Why are posters not showing up in my notifications?
**A:** Posters are only available for notification agents which have the "[Include Poster Image](./images/include_poster_image.png)" or "[Include Rich Metadata Info](./images/include_rich_metadata_info.png)" options in the settings, with the exception of Email. If you are using any of those agents, make sure you have Imgur upload setup (see the next question), and the poster will automatically be included with notification. For Email, make sure you have "[Enable HTML Support](./images/enable_html_support.png)" checked in the Email settings, then you may use an HTML image tag to add the poster to body of your notification, for example: `<img src="{poster_url}" height="225" width="150">`

#### <a id="imgur">Q:</a> How do I set up Imgur for notification posters?
**A:** First you must create an [Imgur account](https://imgur.com/register), then register a new application [here](https://api.imgur.com/oauth2/addclient). Enter an Application Name, Email, and Description, and select the option "OAuth 2 authorization without a callback URL". You will receive a new `client_id` for your application. Enter this value for the "Imgur Client ID" in the Tautulli settings.

#### <a id="notifications-q9">Q:</a> Facebook notifications are telling me "Insufficient permission to post to target on behalf of the viewer".
**A:** When allowing Tautulli to access your Facebook account, you must select `Public` or `Friends` for the app visibility permissions. Selecting `Only Me` will not work.

#### <a id="notifications-q10">Q:</a> Facebook notifications are telling me "Some of the aliases you requested do not exist".
**A:** Your Facebook Group ID is incorrect. If your group has a named URL, you'll need to find the ID number using a tool like [lookup-id.com](https://lookup-id.com). Your group will need to be open in order for that tool to work. You can change the group back to closed/secret once you have the group ID number.

#### <a id="notifications-pycryptodome">Q:</a> I'm seeing a "The PyCryptodome library is missing." message!
**A:** The PyCryptodome library is required to encrypt notifications sent to your Remote Android App. Installation instructions can be found in [their documentation](http://pycryptodome.readthedocs.io/en/latest/src/installation.html#installation).

#### <a id="notifications-text-ignored">Q:</a> Notifications are sending the wrong text/sending the default text.
**A:** When Tautulli encounters custom notification text that it fails to parse, it will fall back to the default text so the notification can still be sent out. Generally this is due to using an invalid `{parameter}` in the text that doesn't exist in Tautulli, or doesn't exist for the specific media item. The error logs will tell you the exact reason your custom text failed to parse, allowing you to correct the mistake.

For example:
```
Tautulli NotificationHandler :: Unable to parse parameter u'foobar' in notification body. Using fallback.
```

#### <a id="notifications-override-python">Q:</a> How do I override the Python version in a script?
**A:** There are two aspects you might want to change:
  1. The `PYTHONPATH` environment variable
      * Tautulli will enhance the `PYTHONPATH` variable with the path of its own bundled libraries, allowing scripts to use any of the bundled libraries without the user needing to have installed them system wide. However, this means that the bundled versions take priority. If you want to disable this feature simply prepend `nopythonpath` to the script arguments.
  
  1. The `python` interpreter used.
      * Normally scripts ending in `.py` are executed with `python`. If you want to change this you can prepend the interpreter in front of the script arguments. Currently allowed overrides: `python2`, `python3`, `python`, `pythonw`, `php`, `ruby`, `perl`.

Examples:
  * If you wanted to run a Python 3 script, _without_ the `PYTHONPATH` changes from Tautulli you would set the arguments to `nopythonpath python3 the other arguments`.

  * If you wanted to run a Python 2 script with python2 instead of python and _use_ the bundled libraries from Tautulli, you would set the arguments to `python2 the other arguments`.

#### <a id="notifications-not-notifying-again">Q:</a> My recently added notifications are not sending and the logs say "Not notifying again".
**A:** Same as the FAQ answer [here](#move-media).

---

### Newsletters

#### <a id="newsletter-recently-added-library">Q:</a> I enabled a library but it's not showing in the newsletter!
**A:** Newsletters use Plex's Recently Added list in order to generate the content for the Newsletter, as such if you have unchecked ["Include in dashboard"](./images/include_in_dashboard.png) in the libraries Advanced settings *in Plex*, then it won't show in the Newsletter.

#### <a id="message-clipped">Q:</a> Gmail is giving me a "Message clipped" message!
**A:** When an email message exceeds a certain size in Gmail it is automatically clipped, requiring you to click a "View entire message" link in order to see the full contents. In order to get the Newsletters to render properly in mail clients they have to be rather complex, leading to this check triggering. Unfortunately there is nothing that can be done about this as reducing the complexity leads to issues with mail clients breaking the rendering of the Newsletter. If you have enabled Self Hosted newsletters a link to view the full message is always the first thing in the message and should be visible no matter what.

#### <a id="newsletter-date-format">Q:</a> How do I edit the date format?
**A:** Newsletters follow the date format specified under Settings -> General -> Date Format.

#### <a id="newsletter-missing-images">Q:</a> Images are not showing up in my newsletter emails.
**A:** The first thing to check is that your image hosting settings are correct. There should be **no** orange warning text under any of the related settings.

If you have enabled self hosted newsletters, or are using self-hosted images, ensure that your Public Tautulli Domain setting under Web Interface is correct.

If you are using Imgur as your image hosting you will likely run into API limits and some images may be missing. It is recommended to use Cloudinary if you are using an external image hosting service.

If you have checked the above and images in the newsletter are working for some users but not others, we have found that some email clients are buggy and do not display the images in the newsletter. Tautulli doesn't support clients that exhibit these issues, if you are interested in supporting these clients please use the [Custom Template](#newsletter-custom-template) functionality. Known problematic clients are the default Mail.app on iOS and some Microsoft Outlook versions.

#### <a id="newsletter-custom-template">Q:</a> I want to customize the newsletter.
**A:** If you want to change something about how the Newsletters look, such as a custom logo, or changing the text, you need to create a folder containing your templates and point Tautulli at it.

It's recommended to copy the current template to start off with. Download [recently_added.html](https://github.com/Tautulli/Tautulli/raw/master/data/interfaces/newsletters/recently_added.html) to a folder of your choice. You can then edit the `recently_added.html` file to match what you would like the newsletters to look like. The templating language in use here is [Mako](http://www.makotemplates.org/).

_Note: Your folder can be located anywhere Tautulli has access to, but the file **must** be named `recently_added.html`._

After you have that set up, you need to tell Tautulli to use the new template. Do this by filling in the **full** path to the folder you created above in the Settings > Notifications & Newsletters > <kbd>Show Advanced</kbd> button > [Custom Newsletter Template Folder](./images/newsletter_custom_template_folder.png) option.

You can view all the raw JSON data available to be used in the newsletter template by adding `&raw=true` to the newsletter preview URL. For example:

    http://localhost:8181/newsletter_preview?newsletter_id=1&raw=true

---

### Windows

#### <a id="windows-q1">Q:</a> I enabled HTTPS but received a warning that the pyOpenSSL module is missing. How do I fix this?
**A:** The pyOpenSSL module is not bundled with Python. Run the following in the command line to install it.

```
python -m pip install pyopenssl
```

If that doesn't work:

1. Download the latest version of pyOpenSSL [here](https://pypi.python.org/pypi/pyOpenSSL#downloads) (the source `.tar.gz` file) and save it to `C:\`.
2. Run `python -m pip install C:\pyOpenSSL-17.5.0.tar.gz`

If you have installed Python into a different directory or saved pyOpenSSL to somewhere else, you have to modify the above command in step 2 accordingly.

#### <a id="windows-q2">Q:</a> Tautulli keeps telling me "You're running an unknown version of Tautulli."
**A:** You most likely forgot the following step when installing Git for  Windows. Run the Git installer again, making sure you include the step below.

> Run the installer, select all the defaults except for the section called "Adjusting your PATH environment" - here select **"Git from the command line and also from 3rd-party software"**.

_Note: If you are seeing this and aren't running Windows, it's likely you are hitting the [SSL error](#ssl-update) FAQ entry!_

#### <a id="windows-q3">Q:</a> When trying to update, the logs say "Invalid update data, update failed."
**A:** Delete the `update` folder inside the Tautulli directory and try updating again.

#### <a id="windows-q4">Q:</a> I am getting a "DatabaseError: file is encrypted or is not a database"!
**A:** This seems to be a version mismatch with the packaged Python sqlite3 libraries. Download the latest "Precompiled Binaries for Windows" from [here](https://www.sqlite.org/download.html) and place the extracted `sqlite3.dll`s file in `C:\Python27\DLLs`.

#### <a id="windows-q5">Q:</a> How can I run Tautulli without the command prompt staying open?
**A:** Please refer to the instructions under the [Install as a daemon](Install-as-a-daemon#windows) wiki.

#### <a id="windows-q6">Q:</a> The command prompt just flashes open then closes immediately when starting Tautulli.
**A:** Start Tautulli manually from the command prompt to view the error. Open the Windows command prompt then running the following command. Fill in `C:\path\to\tautulli` to match the path where Tautulli is installed.

```batch
& 'C:\Program Files\Python38\python.exe' "C:\path\to\tautulli\Tautulli.py"
```

Then refer to [this FAQ](#general-q1) above.


---

### OSX

#### <a id="osx-q1">Q:</a> When trying to update, the logs say "Agreeing to the Xcode/iOS license requires admin privileges, please re-run as root via sudo."
**A:** Run the following command in the terminal (according to this [Stackoverflow answer](http://stackoverflow.com/a/26772631)):

```
sudo xcode-select --install
```

#### <a id="osx-unknown-locale">Q:</a> I'm getting a `ValueError: unknown locale: UTF-8` message
**A:** If you are seeing this error when trying to start Tautulli the simple fix is to add these lines to your `~/.bash_profile` file:

```sh
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
```

To make this change active you can either restart Terminal, or run the following:
```sh
source ~/.bash_profile
```

#### <a id="osx-python-dock">Q:</a> How do I get rid of the Python rocket icon in my dock?
**A:** Unfortunately, the Python dock icon is required when the menu bar icon is enabled and you are running Tautulli using Python directly. You can either disable the menu bar icon, or reinstall Tautulli using the macOS pkg instead (refer to this [[wiki page|Upgrading to Python 3 (Tautulli v2.5)#windows--macos]] for details). The pkg install will not show any dock icons regardless if the menu bar icon is enabled or disabled.


---

### QNAP

#### <a id="qnap-q1">Q:</a> How do I set the Plex Logs Folder on QNAP?
**A:** When running a Plex Media Server on a QNAP, Plex writes logs into a non-shared location with the `/share/.qpkg` path. Tautulli cannot be pointed to this location and you need to create a symbolic link.

1. SSH into your QNAP device.
2. Create a directory in a shared folder that will be accessible:

    ```
    mkdir /share/MD0_DATA/PATH/TO/VALID/SHARE/FOLDER/PlexLogs
    ```

3. Create symbolic link between unshared log folder and new shared folder:

    ```
    ln -s "/share/MD0_DATA/.qpkg/PlexMediaServer/Library/Plex Media Server/Logs/" "/share/MD0_DATA/PATH/TO/VALID/SHARE/FOLDER/PlexLogs"
    ```

4. Your new location is now usable in Settings > Plex Media Server > <kbd>Show Advanced</kbd> button > Logs Folder:

    ```
    \\<ipaddress>\PATH\TO\VALID\SHARE\FOLDER\PlexLogs
    ```
