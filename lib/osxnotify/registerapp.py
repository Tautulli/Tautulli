#!/usr/bin/python

import shutil
import os
import stat
import platform
import subprocess

def registerapp(app):

    # don't do any of this unless >= 10.8
    if not [int(n) for n in platform.mac_ver()[0].split('.')] >= [10, 8]:
        return None, 'Registering requires OS X version >= 10.8'

    app_path = None

    # check app bundle doesn't already exist
    app_path = subprocess.check_output(['/usr/bin/mdfind', 'kMDItemCFBundleIdentifier == "ade.headphones.osxnotify"']).strip()
    if app_path:
        return app_path, 'App previously registered'

    # check app doesn't already exist
    app = app.strip()
    if not app:
        return None, 'Path/Application not entered'
    if os.path.splitext(app)[1] == ".app":
        app_path = app
    else:
        app_path = app + '.app'
    if os.path.exists(app_path):
        return None, 'App %s already exists, choose a different name' % app_path

    # generate app
    try:
        os.mkdir(app_path)
        os.mkdir(app_path + "/Contents")
        os.mkdir(app_path + "/Contents/MacOS")
        os.mkdir(app_path + "/Contents/Resources")
        shutil.copy(os.path.join(os.path.dirname(__file__), "appIcon.icns"), app_path + "/Contents/Resources/")

        version = "1.0.0"
        bundleName = "OSXNotify"
        bundleIdentifier = "ade.headphones.osxnotify"

        f = open(app_path + "/Contents/Info.plist", "w")
        f.write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleExecutable</key>
    <string>main.py</string>
    <key>CFBundleGetInfoString</key>
    <string>%s</string>
    <key>CFBundleIconFile</key>
    <string>appIcon.icns</string>
    <key>CFBundleIdentifier</key>
    <string>%s</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>%s</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>%s</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleVersion</key>
    <string>%s</string>
    <key>NSAppleScriptEnabled</key>
    <string>YES</string>
    <key>NSMainNibFile</key>
    <string>MainMenu</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
"""     % (bundleName + " " + version, bundleIdentifier, bundleName, bundleName + " " + version, version))
        f.close()

        f = open(app_path + "/Contents/PkgInfo", "w")
        f.write("APPL????")
        f.close()

        f = open(app_path + "/Contents/MacOS/main.py", "w")
        f.write("""#!/usr/bin/python

objc = None

def swizzle(cls, SEL, func):
    old_IMP = cls.instanceMethodForSelector_(SEL)
    def wrapper(self, *args, **kwargs):
        return func(self, old_IMP, *args, **kwargs)
    new_IMP = objc.selector(wrapper, selector=old_IMP.selector,
        signature=old_IMP.signature)
    objc.classAddMethod(cls, SEL, new_IMP)

def notify(title, subtitle=None, text=None, sound=True):
    global objc
    objc = __import__("objc")
    swizzle(objc.lookUpClass('NSBundle'),
        b'bundleIdentifier',
        swizzled_bundleIdentifier)
    NSUserNotification = objc.lookUpClass('NSUserNotification')
    NSUserNotificationCenter = objc.lookUpClass('NSUserNotificationCenter')
    NSAutoreleasePool = objc.lookUpClass('NSAutoreleasePool')
    pool = NSAutoreleasePool.alloc().init()
    notification = NSUserNotification.alloc().init()
    notification.setTitle_(title)
    notification.setSubtitle_(subtitle)
    notification.setInformativeText_(text)
    notification.setSoundName_("NSUserNotificationDefaultSoundName")
    notification_center = NSUserNotificationCenter.defaultUserNotificationCenter()
    notification_center.deliverNotification_(notification)
    del pool

def swizzled_bundleIdentifier(self, original):
    return 'ade.headphones.osxnotify'

if __name__ == '__main__':
    notify('Half Man Half Biscuit', 'Back in the DHSS', '99% Of Gargoyles Look Like Bob Todd')
""")
        f.close()

        oldmode = os.stat(app_path + "/Contents/MacOS/main.py").st_mode
        os.chmod(app_path + "/Contents/MacOS/main.py", oldmode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        return app_path, 'App registered'

    except Exception, e:
        return None, 'Error creating App %s. %s' % (app_path, e)