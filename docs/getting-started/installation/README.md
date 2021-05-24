# Installation

## Windows

{% tabs %}
{% tab title="Recommended Method" %}
Download and run the latest Windows `.exe` installer from the [GitHub Releases page](https://github.com/Tautulli/Tautulli/releases/latest).
{% endtab %}

{% tab title="Alternative 1" %}
{% hint style="danger" %}
The following installation method is _not recommended_.
{% endhint %}

1. Download the latest version of [Python](https://www.python.org/downloads/) and complete the installation with all the default options.
2. Download Tautulli from GitHub: [https://github.com/Tautulli/Tautulli/zipball/master](https://github.com/Tautulli/Tautulli/zipball/master)
3. Extract the ZIP file.
4. Double click `start.bat` to run Tautulli.
5. Tautulli will be loaded in your browser or listening on [http://localhost:8181](http://localhost:8181).
{% endtab %}

{% tab title="Alternative 2" %}
{% hint style="danger" %}
The following installation method is _not recommended_.
{% endhint %}

{% hint style="warning" %}
This will install extra shell extensions and make adjustments to your path environment.
{% endhint %}

1. Go to [https://gitforwindows.org/](https://gitforwindows.org/) and download `git`.
2. Run the installer, select all the defaults except for the section called "Adjusting your PATH environment" - here select **"Git from the command line and also from 3rd-party software"**.
3. Complete the rest of the installation with the default options.
4. Right click on your desktop and select "Git Gui".
5. Select "Clone Existing Repository".
6. In the "Source Location" enter: `https://github.com/Tautulli/Tautulli.git`
7. In the "Target Directory" enter a new folder where you want to install Tautulli to \(e.g. `C:\Tautulli`\).
8. Click "Clone".
9. When it's finished a Git Gui windows will appear, just close this Window.
10. Browse to where you cloned the Tautulli repository \(e.g. `C:\Tautulli`\) in Windows Explorer.
11. Double click `start.bat` to run Tautulli.
12. Tautulli will be loaded in your browser or listening on [http://localhost:8181](http://localhost:8181).
{% endtab %}
{% endtabs %}

## macOS

{% tabs %}
{% tab title="Recommended Method" %}
Download and run the latest macOS `.pkg` installer from the [GitHub Releases page](https://github.com/Tautulli/Tautulli/releases/latest).

{% hint style="info" %}
Note: The `.pkg` installer requires macOS 10.14 \(Mojave\) or newer.
{% endhint %}
{% endtab %}

{% tab title="Alternative 1" %}
{% hint style="danger" %}
The following installation method is _not recommended_.
{% endhint %}

Tautulli will be installed to `/Applications/Tautulli`

1. Download Tautulli from GitHub: [https://github.com/Tautulli/Tautulli/zipball/master](https://github.com/Tautulli/Tautulli/zipball/master)
2. Extract the zip to `/Applications/Tautulli`. Make sure you extract the files directly in the root.
3. Open a terminal.
4. Change directory:

   ```bash
   cd /Applications/Tautulli
   ```

5. Start Tautulli:

   ```bash
   ./start.sh
   ```

6. Tautulli will be loaded in your browser or listening on [http://localhost:8181](http://localhost:8181).
{% endtab %}

{% tab title="Alternative 2" %}
{% hint style="danger" %}
The following installation method is _not recommended_.
{% endhint %}

Tautulli will be installed to `/Applications/Tautulli`.

1. Open a terminal
2. Install Git:

   ```bash
   xcode-select --install
   ```

3. Change directory:

   ```bash
   cd /Applications/
   ```

4. Clone Tautulli:

   ```bash
   git clone https://github.com/Tautulli/Tautulli.git
   ```

5. Change directory:

   ```bash
   cd Tautulli
   ```

6. Start Tautulli:

   ```bash
   ./start.sh
   ```

7. Tautulli will be loaded in your browser or listening on [http://localhost:8181](http://localhost:8181).
{% endtab %}
{% endtabs %}

## Linux

{% tabs %}
{% tab title="Recommended Method" %}
Tautulli can be installed on most Linux distribution using a Snap package.

1. Select your Linux distribution at the bottom of the [Tautulli Snapcraft page](https://snapcraft.io/tautulli) to install `snapd`.
   * If your Linux distribution is not listed, additional instructions can be found [here](https://snapcraft.io/docs/installing-snapd).
2. Install Tautulli:

   ```bash
   sudo snap install tautulli
   ```

3. Tautulli will be loaded in your browser or listening on [http://localhost:8181](http://localhost:8181/).
{% endtab %}

{% tab title="Alternative" %}
{% hint style="danger" %}
The following installation method is _not recommended_.
{% endhint %}

Tautulli will be installed to `/opt/Tautulli`.

1. Open a terminal.
2. Install prerequisites:
   * Ubuntu/Debian:

     ```bash
     sudo apt-get install git python3.7 python3-setuptools
     ```

   * Fedora:

     ```bash
     sudo yum install git python3 python3-setuptools
     ```
3. Change directory:

   ```bash
   cd /opt
   ```

4. Clone Tautulli:

   ```bash
   sudo git clone https://github.com/Tautulli/Tautulli.git
   ```

5. Add the Tautulli user:
   * Ubuntu/Debian:

     ```bash
     sudo addgroup tautulli && sudo adduser --system --no-create-home tautulli --ingroup tautulli
     ```

   * CentOS/Fedora:

     ```bash
     sudo adduser --system --no-create-home tautulli
     ```
6. Change ownership:

   ```bash
   sudo chown -R tautulli:tautulli /opt/Tautulli
   ```

7. Copy the service script:

   ```bash
   sudo cp /opt/Tautulli/init-scripts/init.systemd /lib/systemd/system/tautulli.service
   ```

8. Enable the service:

   ```bash
   sudo systemctl daemon-reload && sudo systemctl enable tautulli.service
   ```

9. Start Tautulli:

   ```bash
   sudo systemctl start tautulli.service
   ```

10. Tautulli will be loaded in your browser or listening on [http://localhost:8181](http://localhost:8181).

{% hint style="info" %}
Refer to the instructions in the [service file](https://github.com/Tautulli/Tautulli/blob/master/init-scripts/init.systemd) to run Tautulli using a different user or move your Tautulli data to a different location.
{% endhint %}
{% endtab %}
{% endtabs %}

## FreeBSD / FreeNAS

{% tabs %}
{% tab title="Recommended Method" %}
Tautulli will be installed to `/usr/local/share/Tautulli`.

1. Create a new jail for Tautulli and open a shell for the jail.
2. Install prerequisites:

   ```bash
   pkg install python py37-setuptools py37-sqlite3 py37-openssl py37-pycryptodomex security/ca_root_nss git-lite
   ```

3. Change directory:

   ```bash
   cd /usr/local/share
   ```

4. Clone Tautulli:

   ```bash
   git clone https://github.com/Tautulli/Tautulli.git
   ```

5. Add the Tautulli user:

   ```bash
   pw useradd -n tautulli -c "Tautulli" -s /sbin/nologin -w no
   ```

6. Change ownership:

   ```bash
   chown -R tautulli:tautulli Tautulli
   ```

7. Copy the service script:

   ```bash
   mkdir -p /usr/local/etc/rc.d && cp /usr/local/share/Tautulli/init-scripts/init.freenas /usr/local/etc/rc.d/tautulli
   ```

8. Enable the service:

   ```bash
   sysrc -f /etc/rc.conf tautulli_user="tautulli" && sysrc -f /etc/rc.conf tautulli_enable="YES"
   ```

9. Start Tautulli:

   ```bash
   service tautulli start
   ```

10. Tautulli will be loaded in your browser or listening on [http://localhost:8181](http://localhost:8181).

{% hint style="info" %}
Refer to the instructions in the [service file](https://github.com/Tautulli/Tautulli/blob/master/init-scripts/init.freebsd) to run Tautulli using a different user or move your Tautulli data to a different location.
{% endhint %}
{% endtab %}
{% endtabs %}

## Docker

{% tabs %}
{% tab title="Basic" %}
Create and run the container \(substitute your `<values>`\):

```bash
docker run -d \
  --name=tautulli \
  --restart=unless-stopped
  -v <path to data>:/config \
  -e PUID=<uid> \
  -e PGID=<gid> \
  -e TZ=<timezone> \
  -p 8181:8181 \
  tautulli/tautulli
```

To update the container it must be removed and recreated:

```bash
# Stop the Tautulli container
docker stop tautulli
# Remove the Tautulli container
docker rm tautulli
# Pull the latest update
docker pull tautulli/tautulli
# Run the Tautulli container with the same parameters as before
docker run -d ...
```
{% endtab %}

{% tab title="Compose" %}
Create a `docker-compose.yml` file with the following contents \(substitute your `<values>`\):

{% code title="docker-compose.yml" %}
```yaml
version: '3'
services:
  tautulli:
    image: tautulli/tautulli
    container_name: tautulli
    restart: unless-stopped
    volumes:
      - <path to data>:/config
    environment:
      - PUID=<uid>
      - PGID=<gid>
      - TZ=<timezone>
    ports:
      - 8181:8181
```
{% endcode %}

Create and start the container \(run the command from the same folder as your `docker-compose.yml` file\):

```bash
docker-compose up -d
```

To update the container:

```bash
# Pull the latest update
docker-compose pull
# Update and restart the container
docker-compose up -d
```
{% endtab %}
{% endtabs %}

### Parameters

You _must_ substitute the `<values>` with your own settings.

Parameters are split into two halves separated by a colon. The left side represents the host and the right side the container.

**Example**: `-p external:internal` - This shows the port mapping from internal to external of the container. So `-p 8181:8181` would expose port `8181` from inside the container to be accessible from the host's IP on port `8181` \(e.g. `http://<host_ip>:8181`\). The internal port _must be_ `8181`, but the external port may be changed \(e.g. `-p 8080:8181`\).

| Parameter | Function | Required / Optional |
| :---: | :--- | :---: |
| `-p 8181:8181` | Port for web UI | Required |
| `-v <path to data>:/config` | Contains Tautulli config and database | Required |
| `-e PUID=<uid>` | User ID \(see below\) | Optional |
| `-e PGID=<gid>` | Group ID \(see below\) | Optional |
| `-e TZ=<timezone>` | Lookup `TZ` value [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) \(e.g. America/Toronto\) | Required |

### User / Group Identifiers

When using data volumes \(`-v` flags\) permissions issues can arise between the host OS and the container. To avoid this issue you can specify the user `PUID` and group `PGID`. Ensure the data volume directory on the host is owned by the same user you specify.

In this instance `PUID=1001` and `PGID=1001`. To find yours use `id user` as below:

```bash
$ id dockeruser
uid=1001(dockeruser) gid=1001(dockergroup) groups=1001(dockergroup)
```

## Synology

You can easily install _Tautulli_ on Synology devices using [Docker](./#docker). Depending on your Synology device you may or may not have Docker pre-installed. If your device is 'unsupported' \(i.e. Docker is not pre-installed or downloadable through the Synology _Package Center_\), follow the guide [here](https://web.archive.org/web/20190730155552/https://tylermade.net/2017/09/28/how-to-install-docker-on-an-unsupported-synology-nas/) and newer versions of the Docker spk found [here](https://archive.synology.com/download/Package/Docker) to install it.

Once you have Docker on your Synology, add the [official image](https://hub.docker.com/r/tautulli/tautulli/) for Tautulli. This is done by opening the Docker program and searching the **Registry** tab for Tautulli. At the time of this write-up, the interface looked like [this](https://imgur.com/EqxJT91). The official image is named `tautulli/tautulli` and it may not be the first option listed. Double-click the image entry to download it. Once downloaded you will see the image show up under your **Image** tab. Before installing the image you will need some additional user information.

Depending on your preference, you can create a unique user on your system for Tautulli, or you can use the default admin user created during your first start-up. You will need the UID and GID of whatever user you have chosen. The steps to obtain these are as follows:

1. SSH into your system using [PuTTy](https://www.putty.org/) \(if on Windows\) or through Terminal \(if on Linux or Mac\). Be sure to use the appropriate username when logging in.
   * If you're having trouble with this, make sure that [SSH is enabled](http://richardsumilang.com/server/synology/diskstation/enable-ssh-access-to-synology-diskstation/) in your _Terminal and SNMP_ settings in your Synology _Control Panel_.
2. Type `id`
3. This will return a line with the `uid` of that user and their primary group `gid`.

   ```text
    [user@nas ~]$ id
    uid=1001(user) gid=1001(user) groups=1001(user)
   ```

Next, you will want to make sure that you have the prerequisite folders for Tautulli to save config files to. Here's an example general/simplified setup:

```text
/root
 └──/docker
     └──/tautulli
         └──/config
```

Obviously, the important folder here is `/root/docker/tautulli/config`. You should ensure that the permissions on this folder allows the user you picked earlier, and will set later, has _full_ rights to the folder. You can fix the permissions by right-clicking on your folders and going to `Properties` and then the `Permission` tab. Assign the appropriate user/group Full Control and if necessary Enable the option _Apply to this folder, sub-folders and files_.

You may need to restart your DiskStation for the change to take effect.

Next, back in the Docker window, double click your `tautulli/tautulli:latest` image to open the _Create Container_ window. On the first menu, name your container whatever you want as long as it is identifiable to you. Next, click _Advanced Settings_ to open a new window. Next, follow the instructions for the following tabs:

* **Advanced Settings**:
  * Enable _Enable auto-restart_
  * If you wish, create a shortcut on the desktop
* **Volume**:
  * Click _Add Folder_ and add the following paths and corresponding Mount Paths.

| File/Folder | Mount Path |
| :--- | :--- |
| `docker/tautulli/config` | `/config` |

* **Port Settings**:
  * Change the _Local Port_ to `8181` to match the _Container Port_. For some reason the default vale of `Auto` almost never works.
  * You may choose a different _Local Port_ if port `8181` is already in use, but you cannot change the _Container Port_.

| Local Port | Container Port | Type |
| :--- | :--- | :--- |
| `8181` | `8181` | `TCP` |

* **Environment**:
  * Add the following _variables_ and their respective _value_

| variable | value |
| :--- | :--- |
| `PUID` | `uid` from your ssh session, eg. `1001` |
| `PGID` | `gid` from your ssh session, eg. `1001` |
| `TZ` | Lookup `TZ` value [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) \(eg. `America/Los_Angeles`\) |

Finalize the container by applying the _advanced settings_ and then following the remaining prompts.

If your container doesn't immediately run, launch it from the Docker window and give it a few dozen seconds to start completely. Your _Tautulli_ installation should now be accessible via port `8181` \(or your other _Local Port_\) on your DiskStation's local IP address. You can find this under Control Panel -&gt; Network -&gt; Network Interface under `LAN1` or `LAN2`. For example if it shows `192.168.0.5`, then Tautulli can be found at `http://192.168.0.5:8181/`.

### Updating the Container

* See [here](https://mendesconsulting.net/2018/03/26/updating-docker-containers-on-synology/) for instructions on updating a Docker container on Synology.

## Western Digital

{% tabs %}
{% tab title="Docker" %}
Installing using [Docker](./#docker) is recommended if it is supported by your NAS.
{% endtab %}

{% tab title="Package" %}
{% hint style="warning" %}
The package is created and maintained by a third party. For support, please contact the creator
{% endhint %}

You can install Tautulli on Western Digital devices using the [WD package by Tfl](https://community.wd.com/t/package-tautulli-plexpy-adds-monitoring-analytics-and-notifications-for-your-plex-server/217773).
{% endtab %}
{% endtabs %}

## QNAP

{% tabs %}
{% tab title="Docker" %}
Installing using [Docker](./#docker) is recommended if it is supported by your NAS.
{% endtab %}

{% tab title="Package" %}
{% hint style="warning" %}
The package is created and maintained by a third party. For support, please contact the creator
{% endhint %}

You can install Tautulli on QNAP devices using the `.qpkg` by QNAP\_Stephane:

* [QNAP Club](https://qnapclub.eu/en/qpkg/557)
* [QNAP forum thread](https://forum.qnap.com/viewtopic.php?f=320&t=139879)
{% endtab %}
{% endtabs %}

## ReadyNAS

{% tabs %}
{% tab title="Docker" %}
Installing using [Docker](./#docker) is recommended if it is supported by your NAS.
{% endtab %}

{% tab title="Package" %}
{% hint style="warning" %}
The package is created and maintained by a third party. For support, please contact the creator
{% endhint %}

You can install Tautulli on ReadyNAS devices using the [ReadyNAS app by Mhynlo](http://apps.readynas.com/pages/?page_id=9).
{% endtab %}
{% endtabs %}

## Thecus NAS

{% tabs %}
{% tab title="Docker" %}
Installing using [Docker](./#docker) is recommended if it is supported by your NAS.
{% endtab %}

{% tab title="Package" %}
{% hint style="warning" %}
The package is created and maintained by a third party. For support, please contact the creator
{% endhint %}

You can install Tautulli on Thecus devices using the [Thecus app by outkastm](https://forum.thecus.com/showthread.php?tid=12768&pid=70628#pid70628).
{% endtab %}
{% endtabs %}

## ArchLinux

{% tabs %}
{% tab title="Docker" %}
Installing using [Docker](./#docker) is recommended if it is supported by your machine.
{% endtab %}

{% tab title="Package" %}
{% hint style="warning" %}
The package is created and maintained by a third party. For support, please contact the creator
{% endhint %}

You can install Tautulli on ArchLinux using the [AUR package by fryfrog/Sonic-Y3k](https://aur.archlinux.org/packages/tautulli/).
{% endtab %}
{% endtabs %}

