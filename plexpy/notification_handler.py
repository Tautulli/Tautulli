#  This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

from plexpy import logger, config, notifiers

import plexpy


def push_nofitications(push_message=None, subject=None, status_message=None):

    if push_message:
        if not subject:
            subject = 'PlexPy'

        if plexpy.CONFIG.GROWL_ENABLED:
            logger.info(u"Growl request")
            growl = notifiers.GROWL()
            growl.notify(push_message, status_message)

        if plexpy.CONFIG.PROWL_ENABLED:
            logger.info(u"Prowl request")
            prowl = notifiers.PROWL()
            prowl.notify(push_message, status_message)

        if plexpy.CONFIG.XBMC_ENABLED:
            xbmc = notifiers.XBMC()
            if plexpy.CONFIG.XBMC_NOTIFY:
                xbmc.notify(subject, push_message)

        if plexpy.CONFIG.PLEX_ENABLED:
            plex = notifiers.Plex()
            if plexpy.CONFIG.PLEX_NOTIFY:
                plex.notify(subject, push_message)

        if plexpy.CONFIG.NMA_ENABLED:
            nma = notifiers.NMA()
            nma.notify(subject, push_message)

        if plexpy.CONFIG.PUSHALOT_ENABLED:
            logger.info(u"Pushalot request")
            pushalot = notifiers.PUSHALOT()
            pushalot.notify(push_message, status_message)

        if plexpy.CONFIG.PUSHOVER_ENABLED:
            logger.info(u"Pushover request")
            pushover = notifiers.PUSHOVER()
            pushover.notify(push_message, status_message)

        if plexpy.CONFIG.PUSHBULLET_ENABLED:
            logger.info(u"PushBullet request")
            pushbullet = notifiers.PUSHBULLET()
            pushbullet.notify(push_message, status_message)

        if plexpy.CONFIG.TWITTER_ENABLED:
            logger.info(u"Sending Twitter notification")
            twitter = notifiers.TwitterNotifier()
            twitter.notify_download(push_message)

        if plexpy.CONFIG.OSX_NOTIFY_ENABLED:
            # TODO: Get thumb in notification
            # from plexpy import cache
            # c = cache.Cache()
            # album_art = c.get_artwork_from_cache(None, release['AlbumID'])
            logger.info(u"Sending OS X notification")
            osx_notify = notifiers.OSX_NOTIFY()
            osx_notify.notify(subject, push_message)

        if plexpy.CONFIG.BOXCAR_ENABLED:
            logger.info(u"Sending Boxcar2 notification")
            boxcar = notifiers.BOXCAR()
            boxcar.notify(subject, push_message)

        if plexpy.CONFIG.EMAIL_ENABLED:
            logger.info(u"Sending Email notification")
            email = notifiers.Email()
            email.notify(subject=subject, message=push_message)
    else:
        logger.warning('Notification requested but no message received.')