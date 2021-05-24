### Operating Systems:

* [Windows](#windows)
* [macOS](#macos)
* [Linux](#linux)
* [FreeBSD / FreeNAS](#freebsd--freenas)
* [Docker](#docker)
* [Synology](#synology)
* [Western Digital](#western-digital) (Third party)
* [QNAP](#qnap) (Third party)
* [ReadyNAS](#readynas) (Third party)
* [Thecus NAS](#thecus-nas) (Third party)
* [ArchLinux](#archlinux) (Third party)

----

## Windows

Download and run the latest Windows `.exe` installer from the [GitHub Releases page](https://github.com/Tautulli/Tautulli/releases/latest).

<details>
<summary>Alternate installation instructions</summary>

* Download the latest version of [Python](https://www.python.org/downloads/) and complete the installation with all the default options.

* Option 1 (easy):
  * Download Tautulli from GitHub: https://github.com/Tautulli/Tautulli/zipball/master
  * Extract the ZIP file.
  * Double click `start.bat` to run Tautulli.
  * Tautulli will be loaded in your browser or listening on http://localhost:8181.

* Option 2 (preferred):
  > **NOTE**: This will install extra shell extensions and make adjustments to your path environment.

  * Go to https://gitforwindows.org/ and download `git`.
  * Run the installer, select all the defaults except for the section called "Adjusting your PATH environment" - here select **"Git from the command line and also from 3rd-party software"**.
  * Complete the rest of the installation with the default options.
  * Right click on your desktop and select "Git Gui".
  * Select "Clone Existing Repository".
  * In the "Source Location" enter: `https://github.com/Tautulli/Tautulli.git`
  * In the "Target Directory" enter a new folder where you want to install Tautulli to (e.g. `C:\Tautulli`).
  * Click "Clone".
  * When it's finished a Git Gui windows will appear, just close this Window.
  * Browse to where you cloned the Tautulli repository (e.g. `C:\Tautulli`) in Windows Explorer.
  * Double click `start.bat` to run Tautulli.
  * Tautulli will be loaded in your browser or listening on http://localhost:8181.
</details>

## macOS

Download and run the latest macOS `.pkg` installer from the [GitHub Releases page](https://github.com/Tautulli/Tautulli/releases/latest).

* Note: The `.pkg` installer requires macOS 10.14 (Mojave) or newer. For macOS 10.13 (High Sierra) and older please use the alternate installation instructions below.

<details>
<summary>Alternate installation instructions</summary>

Tautulli will be installed to `/Applications/Tautulli`

* Option 1 (easy):
  * Download Tautulli from GitHub: https://github.com/Tautulli/Tautulli/zipball/master
  * Extract the zip to `/Applications/Tautulli`. Make sure you extract the files directly in the root.
  * Open a terminal
  * Type: `cd /Applications/Tautulli`
* Option 2 (preferred):
  * Open a terminal
  * Install Git. This can be done via `xcode-select --install`
  * Type: `cd /Applications/`
  * Type: `git clone https://github.com/Tautulli/Tautulli.git`
  * Type: `cd Tautulli`
* Type: `./start.sh` to run Tautulli.
* Tautulli will be loaded in your browser or listening on http://localhost:8181.
</details>

## Linux

Tautulli can be installed on most Linux distribution using a Snap.

1. Select your Linux distribution at the bottom of the [Tautulli Snapcraft page](https://snapcraft.io/tautulli) to install `snapd`.
    * If your Linux distribution is not listed, additional instructions can be found [here](https://snapcraft.io/docs/installing-snapd).
1. Install Tautulli: `sudo snap install tautulli`
1. Tautulli will be loaded in your browser or listening on http://localhost:8181/

<details>
<summary>Alternate installation instructions</summary>

Tautulli will be installed to `/opt/Tautulli`.

1. Open a terminal.
1. Install prerequisites:
    * Ubuntu/Debian: `sudo apt-get install git python3.7 python3-setuptools`
    * Fedora: `sudo yum install git python3 python3-setuptools`
1. Change directory: `cd /opt`
1. Clone Tautulli: `sudo git clone https://github.com/Tautulli/Tautulli.git`
1. Add the Tautulli user:
    * Ubuntu/Debian: `sudo addgroup tautulli && sudo adduser --system --no-create-home tautulli --ingroup tautulli`
    * CentOS/Fedora: `sudo adduser --system --no-create-home tautulli`
1. Change ownership: `sudo chown -R tautulli:tautulli /opt/Tautulli`
1. Copy the service script: `sudo cp /opt/Tautulli/init-scripts/init.systemd /lib/systemd/system/tautulli.service`
1. Enable the service: `sudo systemctl daemon-reload && sudo systemctl enable tautulli.service`
1. Start Tautulli: `sudo systemctl start tautulli.service`
1. Tautulli will be loaded in your browser or listening on http://localhost:8181

#### Note:

* Refer to the instructions in the service file to run Tautulli using a different user or move your Tautulli data to a different location:
  * https://github.com/Tautulli/Tautulli/blob/master/init-scripts/init.systemd
</details>


## FreeBSD / FreeNAS

Tautulli will be installed to `/usr/local/share/Tautulli`.

1. Create a new jail for Tautulli and open a terminal for the jail.
1. Install prerequisites:
`pkg install python py37-setuptools py37-sqlite3 py37-openssl py37-pycryptodomex security/ca_root_nss git-lite`
1. Change directory: `cd /usr/local/share`
1. Clone Tautulli: `git clone https://github.com/Tautulli/Tautulli.git`
1. Add the Tautulli user: `pw useradd -n tautulli -c "Tautulli" -s /sbin/nologin -w no`
1. Change ownership: `chown -R tautulli:tautulli Tautulli`
1. Copy the service script: `mkdir -p /usr/local/etc/rc.d && cp /usr/local/share/Tautulli/init-scripts/init.freenas /usr/local/etc/rc.d/tautulli`
1. Enable the service: `sysrc -f /etc/rc.conf tautulli_user="tautulli" && sysrc -f /etc/rc.conf tautulli_enable="YES"`
1. Start Tautulli: `service tautulli start`
1. Tautulli will be loaded in your browser or listening on http://localhost:8181

#### Note:

* Refer to the instructions in the service file to run Tautulli using a different user or move your Tautulli data to a different location:
  * https://github.com/Tautulli/Tautulli/blob/master/init-scripts/init.freebsd


## Docker

### Using `docker run`

Create and run the container (substitute your `<values>`):
```sh
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
```sh
# Stop the Tautulli container
docker stop tautulli
# Remove the Tautulli container
docker rm tautulli
# Pull the latest update
docker pull tautulli/tautulli
# Run the Tautulli container with the same parameters as before
docker run -d ...
```

### Using `docker-compose`

Create a `docker-compose.yml` file with the following contents (substitute your `<values>`):
```yml
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

Create and start the container (run the command from the same folder as your `docker-compose.yml` file):
```sh
docker-compose up -d
```

To update the container:
```sh
# Pull the latest update
docker-compose pull
# Update and restart the container
docker-compose up -d
```

### Parameters

You *must* substitute the `<values>` with your own settings.

Parameters are split into two halves separated by a colon. The left side represents the host and the right side the container. 

**Example**: `-p external:internal` - This shows the port mapping from internal to external of the container.
So `-p 8181:8181` would expose port `8181` from inside the container to be accessible from the host's IP on port `8181` (e.g. `http://<host_ip>:8181`). The internal port *must be* `8181`, but the external port may be changed (e.g. `-p 8080:8181`).

| Parameter | Function | Required / Optional |
| :---: | --- | :---: | 
| `-p 8181:8181` | Port for web UI | Required |
| `-v <path to data>:/config` | Contains Tautulli config and database | Required |
| `-e PUID=<uid>` | User ID (see below) | Optional |
| `-e PGID=<gid>` | Group ID (see below) | Optional |
| `-e TZ=<timezone>` | Lookup `TZ` value [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (e.g. America/Toronto) | Required |

### User / Group Identifiers:

When using data volumes (`-v` flags) permissions issues can arise between the host OS and the container. To avoid this issue you can specify the user `PUID` and group `PGID`. Ensure the data volume directory on the host is owned by the same user you specify.

In this instance `PUID=1001` and `PGID=1001`. To find yours use `id user` as below:

```
$ id dockeruser
uid=1001(dockeruser) gid=1001(dockergroup) groups=1001(dockergroup)
```


## Synology

You can easily install *Tautulli* on Synology devices using [Docker](#docker). Depending on your Synology device you may or may not have Docker pre-installed. If your device is 'unsupported' (i.e. Docker is not pre-installed or downloadable through the Synology *Package Center*), follow the guide [here](https://web.archive.org/web/20190730155552/https://tylermade.net/2017/09/28/how-to-install-docker-on-an-unsupported-synology-nas/) and newer versions of the Docker spk found [here](https://archive.synology.com/download/Package/Docker) to install it.

Once you have Docker on your Synology, add the [official image](https://hub.docker.com/r/tautulli/tautulli/) for Tautulli. This is done by opening the Docker program and searching the **Registry** tab for Tautulli. At the time of this write-up, the interface looked like [this](https://imgur.com/EqxJT91). The official image is named `tautulli/tautulli` and it may not be the first option listed. Double-click the image entry to download it. Once downloaded you will see the image show up under your **Image** tab. Before installing the image you will need some additional user information.

Depending on your preference, you can create a unique user on your system for Tautulli, or you can use the default admin user created during your first start-up. You will need the UID and GID of whatever user you have chosen. The steps to obtain these are as follows:

1. SSH into your system using [PuTTy](https://www.putty.org/) (if on Windows) or through Terminal (if on Linux or Mac). Be sure to use the appropriate username when logging in.
	- If you're having trouble with this, make sure that [SSH is enabled](http://richardsumilang.com/server/synology/diskstation/enable-ssh-access-to-synology-diskstation/) in your *Terminal and SNMP* settings in your Synology *Control Panel*.
2. Type `id`
3. This will return a line with the `uid` of that user and their primary group `gid`.
    ```
    [user@nas ~]$ id
    uid=1001(user) gid=1001(user) groups=1001(user)
    ```

Next, you will want to make sure that you have the prerequisite folders for Tautulli to save config files to. Here's an example general/simplified setup:

```
/root
 └──/docker
     └──/tautulli
         └──/config
```

Obviously, the important folder here is `/root/docker/tautulli/config`. You should ensure that the permissions on this folder allows the user you picked earlier, and will set later, has _full_ rights to the folder. You can fix the permissions by right-clicking on your folders and going to `Properties` and then the `Permission` tab. Assign the appropriate user/group Full Control and if necessary Enable the option *Apply to this folder, sub-folders and files*.

You may need to restart your DiskStation for the change to take effect.

Next, back in the Docker window, double click your `tautulli/tautulli:latest` image to open the *Create Container* window. On the first menu, name your container whatever you want as long as it is identifiable to you. Next, click *Advanced Settings* to open a new window. Next, follow the instructions for the following tabs:

- **Advanced Settings**:
    - Enable *Enable auto-restart*
    - If you wish, create a shortcut on the desktop
- **Volume**:
    - Click *Add Folder* and add the following paths and corresponding Mount Paths.

| File/Folder | Mount Path |
| :---- | :---- |
| `docker/tautulli/config` | `/config` |

- **Port Settings**:
    - Change the *Local Port* to `8181` to match the *Container Port*. For some reason the default vale of `Auto` almost never works.
    - You may choose a different *Local Port* if port `8181` is already in use, but you cannot change the *Container Port*.

| Local Port | Container Port | Type |
| :---- | :---- | :---- |
| `8181` | `8181` | `TCP` |

- **Environment**:
    - Add the following *variables* and their respective *value*

| variable | value |
| :---- | :---- |
| `PUID` | `uid` from your ssh session, eg. `1001` |
| `PGID` | `gid` from your ssh session, eg. `1001` |
| `TZ` | Lookup `TZ` value [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (eg. `America/Los_Angeles`) |

Finalize the container by applying the *advanced settings* and then following the remaining prompts.

If your container doesn't immediately run, launch it from the Docker window and give it a few dozen seconds to start completely. Your *Tautulli* installation should now be accessible via port `8181` (or your other *Local Port*) on your DiskStation's local IP address. You can find this under Control Panel -> Network -> Network Interface under `LAN1` or `LAN2`. For example if it shows `192.168.0.5`, then Tautulli can be found at `http://192.168.0.5:8181/`.

### How to update the container

* See [here](https://mendesconsulting.net/2018/03/26/updating-docker-containers-on-synology/) for instructions on updating a Docker container on Synology.

---

### The packages below are created and maintained by a third party. For support, please contact the creator.

## Western Digital

You can install Tautulli on Western Digital devices using the [WD package by Tfl](https://community.wd.com/t/package-tautulli-plexpy-adds-monitoring-analytics-and-notifications-for-your-plex-server/217773).


## QNAP

You can install Tautulli on QNAP devices using the `.qpkg` by QNAP_Stephane:
* [QNAP Club](https://qnapclub.eu/en/qpkg/557)
* [QNAP forum thread](https://forum.qnap.com/viewtopic.php?f=320&t=139879)


## ReadyNAS

You can install Tautulli on ReadyNAS devices using the [ReadyNAS app by Mhynlo](http://apps.readynas.com/pages/?page_id=9).


## Thecus NAS

You can install Tautulli on Thecus devices using the [Thecus app by outkastm](https://forum.thecus.com/showthread.php?tid=12768&pid=70628#pid70628).


## ArchLinux

You can install Tautulli on ArchLinux using the [AUR package by fryfrog/Sonic-Y3k](https://aur.archlinux.org/packages/tautulli/).
