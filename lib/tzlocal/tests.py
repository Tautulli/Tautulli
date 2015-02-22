import sys
import os
from datetime import datetime
import unittest
import pytz
import tzlocal.unix

class TzLocalTests(unittest.TestCase):

    def test_env(self):
        tz_harare = tzlocal.unix._tz_from_env(':Africa/Harare')
        self.assertEqual(tz_harare.zone, 'Africa/Harare')

        # Some Unices allow this as well, so we must allow it:
        tz_harare = tzlocal.unix._tz_from_env('Africa/Harare')
        self.assertEqual(tz_harare.zone, 'Africa/Harare')

        local_path = os.path.split(__file__)[0]
        tz_local = tzlocal.unix._tz_from_env(':' + os.path.join(local_path, 'test_data', 'Harare'))
        self.assertEqual(tz_local.zone, 'local')
        # Make sure the local timezone is the same as the Harare one above.
        # We test this with a past date, so that we don't run into future changes
        # of the Harare timezone.
        dt = datetime(2012, 1, 1, 5)
        self.assertEqual(tz_harare.localize(dt), tz_local.localize(dt))

        # Non-zoneinfo timezones are not supported in the TZ environment.
        self.assertRaises(pytz.UnknownTimeZoneError, tzlocal.unix._tz_from_env, 'GMT+03:00')

    def test_timezone(self):
        # Most versions of Ubuntu
        local_path = os.path.split(__file__)[0]
        tz = tzlocal.unix._get_localzone(_root=os.path.join(local_path, 'test_data', 'timezone'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_zone_setting(self):
        # A ZONE setting in /etc/sysconfig/clock, f ex CentOS
        local_path = os.path.split(__file__)[0]
        tz = tzlocal.unix._get_localzone(_root=os.path.join(local_path, 'test_data', 'zone_setting'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_timezone_setting(self):
        # A ZONE setting in /etc/conf.d/clock, f ex Gentoo
        local_path = os.path.split(__file__)[0]
        tz = tzlocal.unix._get_localzone(_root=os.path.join(local_path, 'test_data', 'timezone_setting'))
        self.assertEqual(tz.zone, 'Africa/Harare')

    def test_only_localtime(self):
        local_path = os.path.split(__file__)[0]
        tz = tzlocal.unix._get_localzone(_root=os.path.join(local_path, 'test_data', 'localtime'))
        self.assertEqual(tz.zone, 'local')
        dt = datetime(2012, 1, 1, 5)
        self.assertEqual(pytz.timezone('Africa/Harare').localize(dt), tz.localize(dt))

if sys.platform == 'win32':

    import tzlocal.win32
    class TzWin32Tests(unittest.TestCase):

        def test_win32(self):
            tzlocal.win32.get_localzone()

if __name__ == '__main__':
    unittest.main()
