#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.


import hashlib
import inspect
import json
import os
import random
import re
import time
import traceback

import cherrypy
import xmltodict

import plexpy
import config
import database
import libraries
import logger
import mobile_app
import users


class API2:
    def __init__(self, **kwargs):
        self._api_valid_methods = self._api_docs().keys()
        self._api_authenticated = False
        self._api_out_type = 'json'  # default
        self._api_msg = None
        self._api_debug = None
        self._api_cmd = None
        self._api_apikey = None
        self._api_callback = None  # JSONP
        self._api_result_type = 'error'
        self._api_profileme = None  # For profiling the api call
        self._api_kwargs = None  # Cleaned kwargs
        self._api_app = False

    def _api_docs(self, md=False):
        """ Makes the api docs. """

        docs = {}
        for f, _ in inspect.getmembers(self, predicate=inspect.ismethod):
            if not f.startswith('_') and not f.startswith('_api'):
                if md is True:
                    docs[f] = inspect.getdoc(getattr(self, f)) if inspect.getdoc(getattr(self, f)) else None
                else:
                    docs[f] = ' '.join(inspect.getdoc(getattr(self, f)).split()) if inspect.getdoc(getattr(self, f)) else None
        return docs

    def docs_md(self):
        """ Return the api docs formatted with markdown."""

        return self._api_make_md()

    def docs(self):
        """ Return the api docs as a dict where commands are keys, docstring are value."""

        return self._api_docs()

    def _api_validate(self, *args, **kwargs):
        """ Sets class vars and remove unneeded parameters. """

        if not plexpy.CONFIG.API_ENABLED:
            self._api_msg = 'API not enabled'

        elif not plexpy.CONFIG.API_KEY:
            self._api_msg = 'API key not generated'

        elif len(plexpy.CONFIG.API_KEY) != 32:
            self._api_msg = 'API key not generated correctly'

        elif 'apikey' not in kwargs:
            self._api_msg = 'Parameter apikey is required'

        elif 'cmd' not in kwargs:
            self._api_msg = 'Parameter cmd is required. Possible commands are: %s' % ', '.join(self._api_valid_methods)

        elif 'cmd' in kwargs and kwargs.get('cmd') not in self._api_valid_methods:
            self._api_msg = 'Unknown command: %s. Possible commands are: %s' % (kwargs.get('cmd', ''), ', '.join(sorted(self._api_valid_methods)))

        self._api_callback = kwargs.pop('callback', None)
        self._api_apikey = kwargs.pop('apikey', None)
        self._api_cmd = kwargs.pop('cmd', None)
        self._api_debug = kwargs.pop('debug', False)
        self._api_profileme = kwargs.pop('profileme', None)
        # Allow override for the api.
        self._api_out_type = kwargs.pop('out_type', 'json')

        if 'app' in kwargs and kwargs.pop('app') == 'true':
            self._api_app = True

        if plexpy.CONFIG.API_ENABLED and not self._api_msg:
            if self._api_apikey == plexpy.CONFIG.API_KEY or (self._api_app and self._api_apikey == mobile_app.TEMP_DEVICE_TOKEN):
                self._api_authenticated = True

            elif self._api_app and mobile_app.get_mobile_device_by_token(self._api_apikey):
                mobile_app.set_last_seen(self._api_apikey)
                self._api_authenticated = True

            else:
                self._api_msg = 'Invalid apikey'
            
            if self._api_authenticated and self._api_cmd in self._api_valid_methods:
                self._api_msg = None
                self._api_kwargs = kwargs

            elif not self._api_authenticated and self._api_cmd in ('get_apikey', 'docs', 'docs_md'):
                self._api_authenticated = True
                # Remove the old error msg
                self._api_msg = None
                self._api_kwargs = kwargs

        if self._api_msg:
            logger.api_debug(u'Tautulli APIv2 :: %s.' % self._api_msg)

        logger.api_debug(u'Tautulli APIv2 :: Cleaned kwargs: %s' % self._api_kwargs)

        return self._api_kwargs

    def get_logs(self, sort='', search='', order='desc', regex='', start=0, end=0, **kwargs):
        """
            Get the Tautulli logs.

            ```
            Required parameters:
                None

            Optional parameters:
                sort (str):         "time", "thread", "msg", "loglevel"
                search (str):       A string to search for
                order (str):        "desc" or "asc"
                regex (str):        A regex string to search for
                start (int):        Row number to start from
                end (int):          Row number to end at

            Returns:
                json:
                    [{"loglevel": "DEBUG",
                      "msg": "Latest version is 2d10b0748c7fa2ee4cf59960c3d3fffc6aa9512b",
                      "thread": "MainThread",
                      "time": "2016-05-08 09:36:51 "
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        logfile = os.path.join(plexpy.CONFIG.LOG_DIR, logger.FILENAME)
        templog = []
        start = int(kwargs.get('start', 0))
        end = int(kwargs.get('end', 0))

        if regex:
            logger.api_debug(u'Tautulli APIv2 :: Filtering log using regex %s' % regex)
            reg = re.compile('u' + regex, flags=re.I)

        for line in open(logfile, 'r').readlines():
            temp_loglevel_and_time = None

            try:
                temp_loglevel_and_time = line.split('- ')
                loglvl = temp_loglevel_and_time[1].split(' :')[0].strip()
                tl_tread = line.split(' :: ')
                if loglvl is None:
                    msg = line.replace('\n', '')
                else:
                    msg = line.split(' : ')[1].replace('\n', '')
                thread = tl_tread[1].split(' : ')[0]
            except IndexError:
                # We assume this is a traceback
                tl = (len(templog) - 1)
                templog[tl]['msg'] += line.replace('\n', '')
                continue

            if len(line) > 1 and temp_loglevel_and_time is not None and loglvl in line:

                d = {
                    'time': temp_loglevel_and_time[0],
                    'loglevel': loglvl,
                    'msg': msg.replace('\n', ''),
                    'thread': thread
                }
                templog.append(d)

        if end > 0 or start > 0:
                logger.api_debug(u'Tautulli APIv2 :: Slicing the log from %s to %s' % (start, end))
                templog = templog[start:end]

        if sort:
            logger.api_debug(u'Tautulli APIv2 :: Sorting log based on %s' % sort)
            templog = sorted(templog, key=lambda k: k[sort])

        if search:
            logger.api_debug(u'Tautulli APIv2 :: Searching log values for %s' % search)
            tt = [d for d in templog for k, v in d.items() if search.lower() in v.lower()]

            if len(tt):
                templog = tt

        if regex:
            tt = []
            for l in templog:
                stringdict = ' '.join('{}{}'.format(k, v) for k, v in l.items())
                if reg.search(stringdict):
                    tt.append(l)

            if len(tt):
                templog = tt

        if order == 'desc':
            templog = templog[::-1]

        return templog

    def get_settings(self, key=''):
        """ Gets all settings from the config file.

            ```
            Required parameters:
                None

            Optional parameters:
                key (str):      Name of a config section to return

            Returns:
                json:
                    {"General": {"api_enabled": true, ...}
                     "Advanced": {"cache_sizemb": "32", ...},
                     ...
                     }
            ```
        """

        interface_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/')
        interface_list = [name for name in os.listdir(interface_dir) if
                          os.path.isdir(os.path.join(interface_dir, name))]

        conf = plexpy.CONFIG._config
        config = {}

        # Truthify the dict
        for k, v in conf.iteritems():
            if isinstance(v, dict):
                d = {}
                for kk, vv in v.iteritems():
                    if vv == '0' or vv == '1':
                        d[kk] = bool(vv)
                    else:
                        d[kk] = vv
                config[k] = d
            if k == 'General':
                config[k]['interface'] = interface_dir
                config[k]['interface_list'] = interface_list

        if key:
            return config.get(key)

        return config

    def sql(self, query=''):
        """ Query the Tautulli database with raw SQL. Automatically makes a backup of
            the database if the latest backup is older then 24h. `api_sql` must be
            manually enabled in the config file.

            ```
            Required parameters:
                query (str):        The SQL query

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        if not plexpy.CONFIG.API_SQL:
            self._api_msg = 'SQL not enabled for the API.'
            return

        if not query:
            self._api_msg = 'No SQL query provided.'
            return

        # allow the user to shoot them self
        # in the foot but not in the head..
        if not len(os.listdir(plexpy.CONFIG.BACKUP_DIR)):
            self.backup_db()
        else:
            # If the backup is less then 24 h old lets make a backup
            if any([os.path.getctime(os.path.join(plexpy.CONFIG.BACKUP_DIR, file_)) < (time.time() - 86400)
                   and file_.endswith('.db') for file_ in os.listdir(plexpy.CONFIG.BACKUP_DIR)]):
                self.backup_db()

        db = database.MonitorDatabase()
        rows = db.select(query)
        return rows

    def backup_config(self):
        """ Create a manual backup of the `config.ini` file."""

        data = config.make_backup()
        self._api_result_type = 'success' if data else 'error'

        return data

    def backup_db(self):
        """ Create a manual backup of the `plexpy.db` file."""

        data = database.make_backup()
        self._api_result_type = 'success' if data else 'error'

        return data

    def restart(self, **kwargs):
        """ Restart Tautulli."""

        plexpy.SIGNAL = 'restart'
        self._api_msg = 'Restarting plexpy'
        self._api_result_type = 'success'

    def update(self, **kwargs):
        """ Check for Tautulli updates on Github."""

        plexpy.SIGNAL = 'update'
        self._api_msg = 'Updating plexpy'
        self._api_result_type = 'success'

    def refresh_libraries_list(self, **kwargs):
        """ Refresh the Tautulli libraries list."""
        data = libraries.refresh_libraries()
        self._api_result_type = 'success' if data else 'error'

        return data

    def refresh_users_list(self, **kwargs):
        """ Refresh the Tautulli users list."""
        data = users.refresh_users()
        self._api_result_type = 'success' if data else 'error'

        return data

    def register_device(self, device_id='', device_name='', friendly_name='', **kwargs):
        """ Registers the Tautulli Android App for notifications.

            ```
            Required parameters:
                device_name (str):        The device name of the Tautulli Android App
                device_id (str):          The OneSignal device id of the Tautulli Android App

            Optional parameters:
                friendly_name (str):      A friendly name to identify the mobile device

            Returns:
                None
            ```
        """
        if not device_id:
            self._api_msg = 'Device registartion failed: no device id provided.'
            self._api_result_type = 'error'
            return

        elif not device_name:
            self._api_msg = 'Device registartion failed: no device name provided.'
            self._api_result_type = 'error'
            return

        result = mobile_app.add_mobile_device(device_id=device_id,
                                              device_name=device_name,
                                              device_token=self._api_apikey,
                                              friendly_name=friendly_name)

        if result:
            self._api_msg = 'Device registration successful.'
            self._api_result_type = 'success'
            mobile_app.TEMP_DEVICE_TOKEN = None
        else:
            self._api_msg = 'Device registartion failed: database error.'
            self._api_result_type = 'error'

        return

    def _api_make_md(self):
        """ Tries to make a API.md to simplify the api docs. """

        head = '''# API Reference\n
The API is still pretty new and needs some serious cleaning up on the backend but should be reasonably functional. There are no error codes yet.

## General structure
The API endpoint is `http://ip:port + HTTP_ROOT + /api/v2?apikey=$apikey&cmd=$command`

Response example (default `json`)
```
{
    "response": {
        "data": [
            {
                "loglevel": "INFO",
                "msg": "Signal 2 caught, saving and exiting...",
                "thread": "MainThread",
                "time": "22-sep-2015 01:42:56 "
            }
        ],
        "message": null,
        "result": "success"
    }
}
```
```
General optional parameters:

    out_type:   "json" or "xml"
    callback:   "pong"
    debug:      1
```

## API methods'''

        body = ''
        doc = self._api_docs(md=True)
        for k in sorted(doc):
            v = doc.get(k)
            body += '### %s\n' % k
            body += '' if not v else v + '\n'
            body += '\n\n'

        result = head + '\n\n' + body
        return '<pre>' + result + '</pre>'

    def get_apikey(self, username='', password=''):
        """ Get the apikey. Username and password are required
            if auth is enabled. Makes and saves the apikey if it does not exist.

            ```
            Required parameters:
                None

            Optional parameters:
                username (str):     Your Tautulli username
                password (str):     Your Tautulli password

            Returns:
                string:             "apikey"
            ```
         """
        data = None
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        if plexpy.CONFIG.HTTP_USERNAME and plexpy.CONFIG.HTTP_PASSWORD:
            if username == plexpy.CONFIG.HTTP_USERNAME and password == plexpy.CONFIG.HTTP_PASSWORD:
                if plexpy.CONFIG.API_KEY:
                    data = plexpy.CONFIG.API_KEY
                else:
                    data = apikey
                    plexpy.CONFIG.API_KEY = apikey
                    plexpy.CONFIG.write()
            else:
                self._api_msg = 'Authentication is enabled, please add the correct username and password to the parameters'
        else:
            if plexpy.CONFIG.API_KEY:
                data = plexpy.CONFIG.API_KEY
            else:
                # Make a apikey if the doesn't exist
                data = apikey
                plexpy.CONFIG.API_KEY = apikey
                plexpy.CONFIG.write()

        return data

    def _api_responds(self, result_type='error', data=None, msg=''):
        """ Formats the result to a predefined dict so we can hange it the to
            the desired output by _api_out_as """

        if data is None:
            data = {}
        return {"response": {"result": result_type, "message": msg, "data": data}}

    def _api_out_as(self, out):
        """ Formats the response to the desired output """

        if self._api_cmd == 'docs_md':
            return out['response']['data']

        elif self._api_cmd == 'download_log':
            return

        elif self._api_cmd == 'pms_image_proxy':
            cherrypy.response.headers['Content-Type'] = 'image/jpeg'
            return out['response']['data']

        if self._api_out_type == 'json':
            cherrypy.response.headers['Content-Type'] = 'application/json;charset=UTF-8'
            try:
                if self._api_debug:
                    out = json.dumps(out, indent=4, sort_keys=True, ensure_ascii=False).encode('utf-8')
                else:
                    out = json.dumps(out, ensure_ascii=False).encode('utf-8')
                if self._api_callback is not None:
                    cherrypy.response.headers['Content-Type'] = 'application/javascript'
                    # wrap with JSONP call if requested
                    out = self._api_callback + '(' + out + ');'
            # if we fail to generate the output fake an error
            except Exception as e:
                logger.api_exception(u'Tautulli APIv2 :: ' + traceback.format_exc())
                out['message'] = traceback.format_exc()
                out['result'] = 'error'

        elif self._api_out_type == 'xml':
            cherrypy.response.headers['Content-Type'] = 'application/xml'
            try:
                out = xmltodict.unparse(out, pretty=True)
            except Exception as e:
                logger.api_error(u'Tautulli APIv2 :: Failed to parse xml result')
                try:
                    out['message'] = e
                    out['result'] = 'error'
                    out = xmltodict.unparse(out, pretty=True)

                except Exception as e:
                    logger.api_error(u'Tautulli APIv2 :: Failed to parse xml result error message %s' % e)
                    out = '''<?xml version="1.0" encoding="utf-8"?>
                                <response>
                                    <message>%s</message>
                                    <data></data>
                                    <result>error</result>
                                </response>
                          ''' % e

        return out

    def _api_run(self, *args, **kwargs):
        """ handles the stuff from the handler """

        result = {}
        logger.api_debug(u'Tautulli APIv2 :: API called with kwargs: %s' % kwargs)

        self._api_validate(**kwargs)

        if self._api_cmd and self._api_authenticated:
            call = getattr(self, self._api_cmd)

            # Profile is written to console.
            if self._api_profileme:
                from profilehooks import profile
                call = profile(call, immediate=True)

            # We allow this to fail so we get a
            # traceback in the browser
            try:

                result = call(**self._api_kwargs)
            except Exception as e:
                logger.api_error(u'Tautulli APIv2 :: Failed to run %s with %s: %s' % (self._api_cmd, self._api_kwargs, e))
                if self._api_debug:
                    cherrypy.request.show_tracebacks = True
                    # Reraise the exception so the traceback hits the browser
                    raise
                self._api_msg = 'Check the logs'

        ret = None
        # The api decorated function can return different result types.
        # convert it to a list/dict before we change it to the users
        # wanted output
        try:
            if isinstance(result, (dict, list)):
                ret = result
            else:
                raise
        except:
            try:
                ret = json.loads(result)
            except (ValueError, TypeError):
                try:
                    ret = xmltodict.parse(result, attr_prefix='')
                except:
                    pass

        # Fallback if we cant "parse the reponse"
        if ret is None:
            ret = result

        if ret or self._api_result_type == 'success':
            # To allow override for restart etc
            # if the call returns some data we are gonna assume its a success
            self._api_result_type = 'success'
        else:
            self._api_result_type = 'error'

        # Since some of them metods use a api like response for the ui
        # {result: error, message: 'Some shit happend'}
        if isinstance(ret, dict):
            if ret.get('message'):
                self._api_msg = ret.get('message', {})
                ret = {}

            if ret.get('result'):
                self._api_result_type = ret.get('result')

        return self._api_out_as(self._api_responds(result_type=self._api_result_type, msg=self._api_msg, data=ret))
