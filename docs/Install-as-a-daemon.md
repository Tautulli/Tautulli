### These steps are presented as guidelines. Your results may vary, depending on operating system, installation path and other settings.

----

### Operating Systems:

- [Windows](#windows)
  - [Interactive](#interactive)
  - [Non Interactive](#non-interactive)
- [macOS](#macos)
- [Linux](#linux)
- [FreeBSD](#freebsd)
- [FreeNAS](#freenas)

----

## Windows

Running Tautulli in the background on startup can be enabled by checking Tautulli Settings > Web Interface > Launch at System Startup.
  * **Warning**: Make sure to remove any previous Tautulli shortcut from your startup folder or task in Windows Task Scheduler to prevent conflicts with the Tautulli setting! Refer to deprecated instructions below.

<details>
<summary>Deprecated instructions</summary>

### Interactive
This will start Tautulli in the background when you login to Windows without the command prompt.

* Make sure Tautulli is shutdown. `Tautulli > Settings > Shutdown`
* Create a new shortcut ([screenshot](./images/new_shortcut.png)) in your startup folder with
  * Target: `"C:\Program Files\Python38\pythonw.exe" C:\Tautulli\Tautulli.py`
  * Start in: `C:\Program Files\Python38`
* Start Tautulli with the shortcut

### Non Interactive
This will start Tautulli in the background when your computer starts, regardless of whether you are logged in.

* Make sure Tautulli is shutdown. `Tautulli > Settings > Shutdown`
* Create a new text file and [enter the following line](./images/new_command_file.png): 

      Start "C:\Program Files\Python38\pythonw.exe" C:\Tautulli\Tautulli.py

* Save the file in your Tautulli folder as `Tautulli.cmd` (e.g. `C:\Tautulli\Tautulli.cmd`)
* Open the "Run" dialog window (<kbd>Win</kbd>+<kbd>R</kbd>) and run `%windir%\system32\taskschd.msc` to open your Windows Task Scheduler.
* Create a new task with the following settings:
  * [General](./images/create_task_general.png):
    * Name: Tautulli
    * (•) Run whether user is logged on or not
    * Configure for: Windows 10 (select your own Windows version)
  * [Triggers](./images/create_task_triggers.png):
    * Add a new trigger:
      * Begin the task: At startup
      * [✓] Delay task for: 30 seconds (to allow your server to start up, adjust as necessary)
      * Click OK
  * [Actions](./images/create_task_actions.png):
    * Add a new action:
      * Action: Start a program
      * Program/script: `C:\Tautulli\Tautulli.cmd`
      * Click OK
  * [Settings](./images/create_task_settings.png):
    * [✓] Allow task to be run on demand
    * [✓] Run task as soon as possible after a scheduled start is missed
    * [✓] If the task fails, restart every: 1 minute
    * Attempt to restart up to: 3 times
    * [✓] If the running task does not end when requested, force it to stop
    * If the task is already running, then the following rule applies: Do not start a new instance
  * Click OK
* Tautulli should show up in the [list of Active Tasks](./images/list_of_active_tasks.png).
* Double click on the task, then [click "Run" on the right hand side](./images/click_run_on_right.png). The status will change the "Running".
* Once Tautulli has started, the [status should change back to "Ready" and the last run result should say "The operation completed successfully (0x0)"](./images/status_is_ready.png).
* In your Windows Task Manager, there should be a ["pythonw.exe" background process running](./images/pythonw_background_process.png).
</details>

## macOS

Running Tautulli in the background on startup can be enabled by checking Tautulli Settings > Web Interface > Launch at System Startup.
  * **Warning**: Make sure to remove any previous Tautulli `.plist` files in your `LaunchAgents` folder to prevent conflicts with the Tautulli setting! Refer to deprecated instructions below.

<details>
<summary>Deprecated instructions</summary>

Tested on Mac OS X 10.11.3. Assumes Tautulli is installed to `/Applications/Tautulli`

If you need to specify a version of Python, edit `com.Tautulli.tautulli.plist`

* Make sure Tautulli is shutdown. `Tautulli > Settings > Shutdown`
* Create the `~/Library/LaunchAgents` using the following command:

      mkdir -p ~/Library/LaunchAgents

* Copy the `.plist` file with the following command:

      cp /Applications/Tautulli/init-scripts/init.osx ~/Library/LaunchAgents/com.Tautulli.tautulli.plist

* To start Tautulli run the following command:

      launchctl load ~/Library/LaunchAgents/com.Tautulli.tautulli.plist

* To stop Tautulli run the following command:

      launchctl unload ~/Library/LaunchAgents/com.Tautulli.tautulli.plist
</details>


## Linux

Refer to the main [[Installation]] instructions.

<details>
<summary>Deprecated instructions</summary>

Use the following service script for CentOS, Fedora, Debian, Ubuntu, etc. that uses systemd. The instructions are in the script file.
* https://github.com/Tautulli/Tautulli/blob/master/init-scripts/init.systemd
</details>


## FreeBSD

Refer to the main [[Installation]] instructions.

<details>
<summary>Deprecated instructions</summary>

This assumes Tautulli is installed to `/usr/local/share/Tautulli` as per installation instructions, and user is `tautulli`. You can make your own user using: `sudo adduser`

* Make sure Tautulli is shutdown. `Tautulli > Settings > Shutdown`
* Ensure user permissions are correct:

      sudo chown -R tautulli:tautulli /usr/local/share/Tautulli

* Copy init script:

      sudo cp /usr/local/share/Tautulli/init-scripts/init.freebsd /usr/local/etc/rc.d/tautulli

* Enable at boot:

      sudo sysrc tautulli_enable="YES"

* To start:

      sudo service tautulli start

  * You can use `service tautulli [start | stop | restart | status]` to start/stop/restart or check the status of the Tautulli service
  * **Note:** You may ignore the warning `/usr/local/etc/rc.d/tautulli: WARNING: $command_interpreter /usr/local/bin/python3 != python`.

Optional:
* If you need to change user:

      sudo sysrc tautulli_user="USERNAME"

  * Set user permissions for the Tautulli directory:

        chown -R USERNAME:GROUPNAME /usr/local/share/Tautulli

* Run from another directory:

      sudo sysrc tautulli_dir="DIRECTORY"
</details>


## FreeNAS

Refer to the main [[Installation]] instructions.

<details>
<summary>Deprecated instructions</summary>

This assumes Tautulli is installed to `/usr/local/share/Tautulli` as per installation instructions, and user is `root`.

To automate the Tautulli script just do this in the jail shell (in root directory):
* Make sure Tautulli is shutdown. `Tautulli > Settings > Shutdown`
* Ensure user permissions are correct:

      chown -R root:wheel /usr/local/share/Tautulli

* Copy init script:

      cp /usr/local/share/Tautulli/init-scripts/init.freenas /usr/local/etc/rc.d/tautulli

* Set user to run:

      sysrc tautulli_user="root"

* Enable at boot:

      sysrc tautulli_enable="YES"

* To start:

      service tautulli start

  * You can use `service tautulli [start | stop | restart | status]` to start/stop/restart or check the status of the Tautulli service
  * **Note:** You may ignore the warning `/usr/local/etc/rc.d/tautulli: WARNING: $command_interpreter /usr/local/bin/python3 != python`.

Optional:
* If you need to change user:

      sysrc tautulli_user="USERNAME"

  * Set user permissions for the Tautulli directory:

        chown -R USERNAME:GROUPNAME /usr/local/share/Tautulli

* Run from another directory:

      sysrc tautulli_dir="DIRECTORY"
</details>
