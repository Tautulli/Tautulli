#!/usr/bin/python

from xml.dom.minidom import parseString
from httplib import HTTPSConnection
from urllib import urlencode

__version__ = "0.1"

API_SERVER = 'nma.usk.bz'
ADD_PATH   = '/publicapi/notify'

USER_AGENT="PyNMA/v%s"%__version__

def uniq_preserve(seq): # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

def uniq(seq):
    # Not order preserving
    return {}.fromkeys(seq).keys()

class PyNMA(object):
    """PyNMA(apikey=[], developerkey=None)
        takes 2 optional arguments:
            - (opt) apykey:      might me a string containing 1 key or an array of keys
            - (opt) developerkey: where you can store your developer key
    """

    def __init__(self, apikey=[], developerkey=None):
        self._developerkey = None
        self.developerkey(developerkey)
        if apikey:
            if type(apikey) == str:
                apikey = [apikey]
        self._apikey          = uniq(apikey)

    def addkey(self, key):
        "Add a key (register ?)"
        if type(key) == str:
            if not key in self._apikey:
                self._apikey.append(key)
        elif type(key) == list:
            for k in key:
                if not k in self._apikey:
                    self._apikey.append(k)

    def delkey(self, key):
        "Removes a key (unregister ?)"
        if type(key) == str:
            if key in self._apikey:
                self._apikey.remove(key)
        elif type(key) == list:
            for k in key:
                if key in self._apikey:
                    self._apikey.remove(k)

    def developerkey(self, developerkey):
        "Sets the developer key (and check it has the good length)"
        if type(developerkey) == str and len(developerkey) == 48:
            self._developerkey = developerkey

    def push(self, application="", event="", description="", url="", priority=0, batch_mode=False):
        """Pushes a message on the registered API keys.
            takes 5 arguments:
                - (req) application: application name [256]
                - (req) event:       event name       [1000]
                - (req) description: description      [10000]
                - (opt) url:         url              [512]
                - (opt) priority:    from -2 (lowest) to 2 (highest) (def:0)
                - (opt) batch_mode:  call API 5 by 5 (def:False)

            Warning: using batch_mode will return error only if all API keys are bad
            cf: http://nma.usk.bz/api.php
        """
        datas = {
            'application': application[:256].encode('utf8'),
            'event':       event[:1024].encode('utf8'),
            'description': description[:10000].encode('utf8'),
            'priority':    priority
        }

        if url:
            datas['url'] = url[:512]

        if self._developerkey:
            datas['developerkey'] = self._developerkey

        results = {}

        if not batch_mode:
            for key in self._apikey:
                datas['apikey'] = key
                res = self.callapi('POST', ADD_PATH, datas)
                results[key] = res
        else:
            for i in range(0, len(self._apikey), 5):
                datas['apikey'] = ",".join(self._apikey[i:i+5])
                res = self.callapi('POST', ADD_PATH, datas)
                results[datas['apikey']] = res
        return results

    def callapi(self, method, path, args):
        headers = { 'User-Agent': USER_AGENT }
        if method == "POST":
            headers['Content-type'] = "application/x-www-form-urlencoded"
        http_handler = HTTPSConnection(API_SERVER)
        http_handler.request(method, path, urlencode(args), headers)
        resp = http_handler.getresponse()

        try:
            res = self._parse_reponse(resp.read())
        except Exception, e:
            res = {'type':    "pynmaerror",
                   'code':    600,
                   'message': str(e)
                   }
            pass

        return res

    def _parse_reponse(self, response):
        root = parseString(response).firstChild
        for elem in root.childNodes:
            if elem.nodeType == elem.TEXT_NODE: continue
            if elem.tagName == 'success':
                res = dict(elem.attributes.items())
                res['message'] = ""
                res['type']    = elem.tagName
                return res
            if elem.tagName == 'error':
                res = dict(elem.attributes.items())
                res['message'] = elem.firstChild.nodeValue
                res['type']    = elem.tagName
                return res


