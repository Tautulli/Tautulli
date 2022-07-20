[Here](https://github.com/Tautulli/Tautulli-Wiki/wiki/Installation) is the link to the original Tautulli installation Guide. 

### This fork requires Python 3.5 or higher. Some changes to the installation process are required in support of Python 3.

---
### Operating Systems:
- [Windows](#Windows)
- [OSx](#OSx)
- [Linux](#Linux)

---
## Windows
[Video installation guide by Byte My Bits](https://www.youtube.com/watch?v=G2m5UJqHYRs&feature=youtu.be) for Method 2.

* Install the latest version of [Python 3](https://www.python.org/downloads/windows/). Download the Windows x86-64 MSI installer and complete the installation with all the default options.

* Method 1 (easy):
    - Download Tautulli from GitHub: <https://github.com/zSeriesGuy/Tautulli/zipball/master>
    - Extract the ZIP file.
    - Open a command window.
    - CD to where you extracted the Tautulli ZIP file (e.g. `cd C:\Tautulli`).
    - Type: `python3 -m venv .\`
    - Type: `.\scripts\activate`
    - Type: `python3 -m pip install --upgrade pip setuptools pip-tools`
    - Type: `pip3 install -r requirements.txt`
    - Type: `.\scripts\python3 Tautulli.py` to start Tautulli
    - Tautulli will be loaded in your browser or listening on <http://localhost:8181>.
    - To run Tautulli in the background on startup without the console window, refer to [Install as a daemon](https://github.com/Tautulli/Tautulli-Wiki/wiki/Install-as-a-daemon#linux-systemd). Be sure that the start command in your daemon process executes `\scripts\python3` in the folder where you extracted the ZIP file (eg. `C:\Tautulli\scripts\python3`).    

* Method 2 (preferred):
    > **NOTE:** This will install extra shell extensions and make adjustments to your path environment.

    - Go to <https://gitforwindows.org/> and download git.
    - Run the installer, select all the defaults except for the section called "Adjusting your PATH environment" - here select **"Git from the command line and also from 3rd-party software"**.
    - Complete the rest of the installation with the default options.
    - Right click on your desktop and select "Git Gui".
    - Select "Clone Existing Repository".
    - In the "Source Location" enter: `https://github.com/zSeriesGuy/Tautulli.git`
    - In the "Target Directory" enter a new folder where you want to install Tautulli to (e.g. `C:\Tautulli`).
    - Click "Clone".
    - When it's finished a Git Gui windows will appear, just close this Window.
    - Open a command window.
    - CD to where you cloned the Tautulli repository (e.g. `cd C:\Tautulli`).
    - Type: `python3 -m venv .\`
    - Type: `.\scripts\activate`
    - Type: `python3 -m pip install --upgrade pip setuptools pip-tools`
    - Type: `pip3 install -r requirements.txt`
    - Type: `.\scripts\python3 Tautulli.py` to start Tautulli
    - Tautulli will be loaded in your browser or listening on <http://localhost:8181>
    - To run Tautulli in the background on startup without the console window, refer to [Install as a daemon](https://github.com/Tautulli/Tautulli-Wiki/wiki/Install-as-a-daemon#linux-systemd). Be sure that the start command in your daemon process executes `\scripts\python3` in the folder where you extracted the ZIP file (eg. `C:\Tautulli\scripts\python3`).    

## OSx
Tautulli will be installed to `/Applications/Tautulli`.

* Open a terminal
* Install Git  
    - `xcode-select --install`
* Install prerequisites:
    - `sudo apt-get install python3 python3-venv python3-all-dev`
* Type: `cd /Applications`
* Type: `git clone https://github.com/zSeriesGuy/Tautulli.git`
* Type: `cd Tautulli`
* Type: `python3 -m venv /Applications/Tautulli`
* Type: `source /opt/Tautulli/bin/activate`
* Type: `python3 -m pip install --upgrade pip setuptools pip-tools`
* Type: `pip3 install -r /opt/Tautulli/requirements.txt`
* Type: `/Applications/Tautulli/bin/python3 Tautulli.py` to start Tautulli
* Tautulli will be loaded in your browser or listening on <http://localhost:8181>


## Linux
Tautulli will be installed to `/opt/Tautulli`.

* Open a terminal
* Install Git  
    - Ubuntu/Debian: `sudo apt-get install git-core`
* Install prerequisites:
    - `sudo apt-get install python3 python3-venv python3-all-dev`
* Type: `cd /opt`
* Type: `sudo git clone https://github.com/zSeriesGuy/Tautulli.git`
* Optional:  
    - Ubuntu/Debian: `sudo addgroup tautulli && sudo adduser --system --no-create-home tautulli --ingroup tautulli`
    - `sudo chown tautulli:tautulli -R /opt/Tautulli`
* Type: `cd Tautulli`
* Type: `python3 -m venv /opt/Tautulli`
* Type: `source /opt/Tautulli/bin/activate`
* Type: `python3 -m pip install --upgrade pip setuptools pip-tools`
* Type: `pip3 install -r /opt/Tautulli/requirements.txt`
* Type: `/opt/Tautulli/bin/python3 Tautulli.py` to start Tautulli
* Tautulli will be loaded in your browser or listening on <http://localhost:8181>
* To run Tautulli in the background on startup without the console window, refer to [Install as a daemon](https://github.com/Tautulli/Tautulli-Wiki/wiki/Install-as-a-daemon#linux-systemd). Be sure that the start command in your daemon process executes `/opt/Tautulli/bin/python3`.
