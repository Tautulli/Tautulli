# Tautulli

This repo of Tautulli is a fork of the original work found [here](https://github.com/Tautulli/Tautulli).

It has been modified primarily to support multiple Plex Media Servers.

Due to the volume of changes and my lack of understanding of creating smaller commits, this fork will most likely never be incorporated into the original product.

##### As such, this is an unofficial fork and is not supported by the original support channels for Tautulli.
##### If you are upgrading an official Tautulli instance, please be sure to back up your config.ini and tautulli.db. This upgrade will irreversibly migrate your database to the new format required for this fork. 

If you experience any issues, please open an issue request on [this](https://github.com/zSeriesGuy/Tautulli/issues) repo.

### Features
- Supports multiple Plex.TV accounts and PMS servers.
- Supports monitoring rclone mount and includes a notification of up/down status.
- Import of Tautulli databases to facilitate consolidation of Tautulli data.
- Multiple levels of Guest Users. A guest user that you allow to log on to Tautulli can be assigned a Guest Access Level that allows them to see more than just their own information.  
    Guest Access Levels:  
    - None - No logon access
    - Guest - Same as the original Guest access.
    - PowerGuest - Can see full information, but only for those servers that the user has shared access to.
    - SuperGuest - Can see full information on all servers.
    - Admin - Access to all administration functions of monitored servers but no access to Tautulli-specific administrative functions.
- Python 3 support. This version now requires Python 3.5 or higher.
- Replaced all shipped python packages with the use of python virtual environments and a requirements.txt.

## Installation and Support
* Read the [Installation Guides](https://github.com/zSeriesGuy/Tautulli/wiki/Installation) for instructions to install Tautulli.
* Support is available on [this repo](https://github.com/zSeriesGuy/Tautulli/issues) only for this fork of Tautulli.
 