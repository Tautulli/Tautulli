# -*- coding: utf-8 -*-

_ENABLED = True
try:
    from Foundation import NSUserNotification, NSUserNotificationCenter
except ImportError:
    _ENABLED = False

import datetime
import os
import sys
import traceback

import Foundation

from . import _internal
from . import compat
from . import events


def on_notification(f):
    """Decorator for registering a function to serve as a "notification center"
    for the application. This function will receive the data associated with an
    incoming macOS notification sent using :func:`rumps.notification`. This
    occurs whenever the user clicks on a notification for this application in
    the macOS Notification Center.

    .. code-block:: python

        @rumps.notifications
        def notification_center(info):
            if 'unix' in info:
                print 'i know this'

    """
    return events.on_notification.register(f)


def _gather_info_issue_9():  # pragma: no cover
    missing_plist = False
    missing_bundle_ident = False
    info_plist_path = os.path.join(os.path.dirname(sys.executable), 'Info.plist')
    try:
        with open(info_plist_path) as f:
            import plistlib
            try:
                load_plist = plistlib.load
            except AttributeError:
                load_plist = plistlib.readPlist
            try:
                load_plist(f)['CFBundleIdentifier']
            except Exception:
                missing_bundle_ident = True

    except IOError as e:
        import errno
        if e.errno == errno.ENOENT:  # No such file or directory
            missing_plist = True

    info = '\n\n'
    if missing_plist:
        info += 'In this case there is no file at "%(info_plist_path)s"'
        info += '\n\n'
        confidence = 'should'
    elif missing_bundle_ident:
        info += 'In this case the file at "%(info_plist_path)s" does not contain a value for "CFBundleIdentifier"'
        info += '\n\n'
        confidence = 'should'
    else:
        confidence = 'may'
    info += 'Running the following command %(confidence)s fix the issue:\n'
    info += '/usr/libexec/PlistBuddy -c \'Add :CFBundleIdentifier string "rumps"\' %(info_plist_path)s\n'
    return info % {'info_plist_path': info_plist_path, 'confidence': confidence}


def _default_user_notification_center():
    notification_center = NSUserNotificationCenter.defaultUserNotificationCenter()
    if notification_center is None:  # pragma: no cover
        info = (
            'Failed to setup the notification center. This issue occurs when the "Info.plist" file '
            'cannot be found or is missing "CFBundleIdentifier".'
        )
        try:
            info += _gather_info_issue_9()
        except Exception:
            pass
        raise RuntimeError(info)
    else:
        return notification_center


def _init_nsapp(nsapp):
    if _ENABLED:
        try:
            notification_center = _default_user_notification_center()
        except RuntimeError:
            pass
        else:
            notification_center.setDelegate_(nsapp)


@_internal.guard_unexpected_errors
def _clicked(ns_user_notification_center, ns_user_notification):
    from . import rumps

    ns_user_notification_center.removeDeliveredNotification_(ns_user_notification)
    ns_dict = ns_user_notification.userInfo()
    if ns_dict is None:
        data = None
    else:
        dumped = ns_dict['value']
        app = getattr(rumps.App, '*app_instance', rumps.App)
        try:
            data = app.serializer.loads(dumped)
        except Exception:
            traceback.print_exc()
            return

    # notification center function not specified => no error but log warning
    if not events.on_notification.callbacks:
        rumps._log(
            'WARNING: notification received but no function specified for '
            'answering it; use @notifications decorator to register a function.'
        )
    else:
        notification = Notification(ns_user_notification, data)
        events.on_notification.emit(notification)


def notify(title, subtitle, message, data=None, sound=True,
           action_button=None, other_button=None, has_reply_button=False,
           icon=None, ignoreDnD=False):
    """Send a notification to Notification Center (OS X 10.8+). If running on a
    version of macOS that does not support notifications, a ``RuntimeError``
    will be raised. Apple says,

        "The userInfo content must be of reasonable serialized size (less than
        1k) or an exception will be thrown."

    So don't do that!

    :param title: text in a larger font.
    :param subtitle: text in a smaller font below the `title`.
    :param message: text representing the body of the notification below the
                    `subtitle`.
    :param data: will be passed to the application's "notification center" (see
                 :func:`rumps.notifications`) when this notification is clicked.
    :param sound: whether the notification should make a noise when it arrives.
    :param action_button: title for the action button.
    :param other_button: title for the other button.
    :param has_reply_button: whether or not the notification has a reply button.
    :param icon: the filename of an image for the notification's icon, will
                 replace the default.
    :param ignoreDnD: whether the notification should ignore do not disturb,
                 e.g., appear also while screen sharing.
    """
    from . import rumps

    if not _ENABLED:
        raise RuntimeError('OS X 10.8+ is required to send notifications')

    _internal.require_string_or_none(title, subtitle, message)

    notification = NSUserNotification.alloc().init()

    notification.setTitle_(title)
    notification.setSubtitle_(subtitle)
    notification.setInformativeText_(message)

    if data is not None:
        app = getattr(rumps.App, '*app_instance', rumps.App)
        dumped = app.serializer.dumps(data)
        objc_string = _internal.string_to_objc(dumped)
        ns_dict = Foundation.NSMutableDictionary.alloc().init()
        ns_dict.setDictionary_({'value': objc_string})
        notification.setUserInfo_(ns_dict)

    if icon is not None:
        notification.set_identityImage_(rumps._nsimage_from_file(icon))
    if sound:
        notification.setSoundName_("NSUserNotificationDefaultSoundName")
    if action_button:
        notification.setActionButtonTitle_(action_button)
        notification.set_showsButtons_(True)
    if other_button:
        notification.setOtherButtonTitle_(other_button)
        notification.set_showsButtons_(True)
    if has_reply_button:
        notification.setHasReplyButton_(True)
    if ignoreDnD:
        notification.set_ignoresDoNotDisturb_(True)

    notification.setDeliveryDate_(Foundation.NSDate.dateWithTimeInterval_sinceDate_(0, Foundation.NSDate.date()))
    notification_center = _default_user_notification_center()
    notification_center.scheduleNotification_(notification)


class Notification(compat.collections_abc.Mapping):
    def __init__(self, ns_user_notification, data):
        self._ns = ns_user_notification
        self._data = data

    def __repr__(self):
        return '<{0}: [data: {1}]>'.format(type(self).__name__, repr(self._data))

    @property
    def title(self):
        return compat.text_type(self._ns.title())

    @property
    def subtitle(self):
        return compat.text_type(self._ns.subtitle())

    @property
    def message(self):
        return compat.text_type(self._ns.informativeText())

    @property
    def activation_type(self):
        activation_type = self._ns.activationType()
        if activation_type == 1:
            return 'contents_clicked'
        elif activation_type == 2:
            return 'action_button_clicked'
        elif activation_type == 3:
            return 'replied'
        elif activation_type == 4:
            return 'additional_action_clicked'

    @property
    def delivered_at(self):
        ns_date = self._ns.actualDeliveryDate()
        seconds = ns_date.timeIntervalSince1970()
        dt = datetime.datetime.fromtimestamp(seconds)
        return dt

    @property
    def response(self):
        ns_attributed_string = self._ns.response()
        if ns_attributed_string is None:
            return None
        ns_string = ns_attributed_string.string()
        return compat.text_type(ns_string)

    @property
    def data(self):
        return self._data

    def _check_if_mapping(self):
        if not isinstance(self._data, compat.collections_abc.Mapping):
            raise TypeError(
                'notification cannot be used as a mapping when data is not a '
                'mapping'
            )

    def __getitem__(self, key):
        self._check_if_mapping()
        return self._data[key]

    def __iter__(self):
        self._check_if_mapping()
        return iter(self._data)

    def __len__(self):
        self._check_if_mapping()
        return len(self._data)
