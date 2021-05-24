# Upgrading to Python 3

## Windows / macOS

### Important changes

Running Tautulli in the background on startup can be enabled by checking Tautulli Settings &gt; Web Interface &gt; Launch at System Startup.

* **Warning**: Make sure to remove any previous Tautulli shortcut from your startup folder or task in Windows Task Scheduler on Windows, or `.plist` files in your `LaunchAgents` folder on macOS, to prevent conflicts with the Tautulli setting! Refer to the deprecated instructions in the \[\[Install as a Daemon\]\] page.

### Reinstalling Tautulli using the app installer \(recommended\)

* Tautulli v2.5 and above can be installed on Windows or macOS \(10.14 or newer\) _without_ needing to install Python. You can download the new Windows `.exe` or macOS `.pkg` installer from the [GitHub Releases page](https://github.com/Tautulli/Tautulli/releases/latest).

#### Instructions:

1. Go to the Tautulli Settings &gt; Help & Info page.
2. Click on the "Database File" link to download a copy of your Tautulli database.
3. Click on the "Configuration File" link to download a copy of your Tautulli configuration.
4. Shutdown Tautulli.
5. Install Tautulli using the Windows `.exe` or macOS `.pkg` installer.
6. Start Tautulli and complete the setup wizard.
7. Go to the Tautulli Settings &gt; Import & Backup page and re-import the database file \(using the "Overwrite" method\) and configuration file that you saved in the steps above.
8. Once you have the database imported and Tautulli successfully configured, you may uninstall the previous version of Tautulli by deleting the old folder \(Windows: `C:\Tautulli` or macOS: `/Applications/Tautulli`\).

#### Notes:

* Python still needs to be installed if you are running Python script notifications.
* To update Tautulli using the app installer, just download and run the new installer when a new update is available.

## Linux

### Reinstalling Tautulli using the Snap package \(recommended\)

* Tautulli v2.6.3 and above can be installed on most Linux distributions using the Snap package _without_ needing to install Python.

#### Instructions:

1. Go to the Tautulli Settings &gt; Help & Info page.
2. Click on the "Database File" link to download a copy of your Tautulli database.
3. Click on the "Configuration File" link to download a copy of your Tautulli configuration.
4. Shutdown Tautulli.
5. Install Tautulli using `snap` by following the \[\[Installation \| Installation\#linux\]\] instructions.
6. Start Tautulli and complete the setup wizard.
7. Go to the Tautulli Settings &gt; Import & Backup page and re-import the database file \(using the "Overwrite" method\) and configuration file that you saved in the steps above.
8. Once you have the database imported and Tautulli successfully configured, you may uninstall the previous version of Tautulli by deleting the old folder \(`/opt/Tautulli`\) and the old service file \(`/lib/systemd/system/tautulli.service`\).

#### Notes:

* Python still needs to be installed if you are running Python script notifications.
* Snap packages update automatically outside of Tautulli.

### Modifying an existing Tautulli install \(alternative\)

* This will update an existing Tautulli systemd service script that is using Python 2 to Python 3.

#### Instructions:

1. Make sure Tautulli is shutdown or run `sudo systemctl stop tautulli.service`.
2. Get the path to your `python3` interpreter using `command -v python3`.
   * Note: You may need to replace `python3` with the correct value for your system \(e.g. `python3.7`\).
3. Edit `/lib/systemd/system/tautulli.service`.
4. Add the path to your `python3` interpreter from step 1 to the start of the `ExecStart=` command \(e.g. `/usr/bin/python3`\).
   * Example:

     ```text
     ExecStart=/usr/bin/python3 /opt/Tautulli/Tautulli.py --config /opt/Tautulli/config.ini --datadir /opt/Tautulli --quiet --daemon --nolaunch
     ```
5. Start Tautulli with `sudo systemctl daemon-reload && sudo systemctl start tautulli.service`.

#### Notes:

* If Tautulli will not start with the error `ImportError: bad magic number in 'pkg_resources'`, run the `clean_pyc.sh` file inside the Tautulli `contrib` folder.

  ```text
  cd /opt/Tautulli/contrib
  ./clean_pyc.sh
  ```

## FreeBSD / FreeNAS

### Modifying an existing Tautulli install

* This will update an existing Tautulli service script that is using Python 2 to Python 3.

#### Instructions:

1. Make sure Tautulli is shutdown or run `service tautulli stop`.
2. Install all the prerequisites from the \[\[Installation \| Installation\#freebsd--freenas\]\] instructions.
3. Remove the old symbolic link to Python 2 with `rm /usr/local/bin/python`.
4. Create a new symbolic link to Python 3 with `ln -s /usr/local/bin/python3 /usr/local/bin/python`.
5. Check the python version with `python -V` and it should say Python 3.7.x.
6. Edit `/usr/local/etc/rc.d/tautulli`.
7. Add `command_interpreter="python"` above the `command` line \(line 41\).
   * Example:

     ```text
     command_interpreter="python"
     command="${tautulli_dir}/Tautulli.py"
     command_args="--daemon --pidfile ${tautulli_pid} --quiet --nolaunch ${tautulli_flags}"
     ```
8. Start Tautulli with `service tautulli start`.

#### Notes:

* If Tautulli will not start with the error `ImportError: bad magic number in 'pkg_resources'`, run the `clean_pyc.sh` file inside the Tautulli `contrib` folder.

  ```text
  cd /usr/local/share/Tautulli/contrib
  ./clean_pyc.sh
  ```

