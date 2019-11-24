import datetime
from itertools import count
import os
import threading
import time

from six.moves import range
from six.moves import urllib

import pytest

import cherrypy
from cherrypy.lib import httputil

from cherrypy.test import helper


curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))

gif_bytes = (
    b'GIF89a\x01\x00\x01\x00\x82\x00\x01\x99"\x1e\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x02\x03\x02\x08\t\x00;'
)


class CacheTest(helper.CPWebCase):

    @staticmethod
    def setup_server():

        @cherrypy.config(**{'tools.caching.on': True})
        class Root:

            def __init__(self):
                self.counter = 0
                self.control_counter = 0
                self.longlock = threading.Lock()

            @cherrypy.expose
            def index(self):
                self.counter += 1
                msg = 'visit #%s' % self.counter
                return msg

            @cherrypy.expose
            def control(self):
                self.control_counter += 1
                return 'visit #%s' % self.control_counter

            @cherrypy.expose
            def a_gif(self):
                cherrypy.response.headers[
                    'Last-Modified'] = httputil.HTTPDate()
                return gif_bytes

            @cherrypy.expose
            def long_process(self, seconds='1'):
                try:
                    self.longlock.acquire()
                    time.sleep(float(seconds))
                finally:
                    self.longlock.release()
                return 'success!'

            @cherrypy.expose
            def clear_cache(self, path):
                cherrypy._cache.store[cherrypy.request.base + path].clear()

        @cherrypy.config(**{
            'tools.caching.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [
                ('Vary', 'Our-Varying-Header')
            ],
        })
        class VaryHeaderCachingServer(object):

            def __init__(self):
                self.counter = count(1)

            @cherrypy.expose
            def index(self):
                return 'visit #%s' % next(self.counter)

        @cherrypy.config(**{
            'tools.expires.on': True,
            'tools.expires.secs': 60,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
            'tools.staticdir.root': curdir,
        })
        class UnCached(object):

            @cherrypy.expose
            @cherrypy.config(**{'tools.expires.secs': 0})
            def force(self):
                cherrypy.response.headers['Etag'] = 'bibbitybobbityboo'
                self._cp_config['tools.expires.force'] = True
                self._cp_config['tools.expires.secs'] = 0
                return 'being forceful'

            @cherrypy.expose
            def dynamic(self):
                cherrypy.response.headers['Etag'] = 'bibbitybobbityboo'
                cherrypy.response.headers['Cache-Control'] = 'private'
                return 'D-d-d-dynamic!'

            @cherrypy.expose
            def cacheable(self):
                cherrypy.response.headers['Etag'] = 'bibbitybobbityboo'
                return "Hi, I'm cacheable."

            @cherrypy.expose
            @cherrypy.config(**{'tools.expires.secs': 86400})
            def specific(self):
                cherrypy.response.headers[
                    'Etag'] = 'need_this_to_make_me_cacheable'
                return 'I am being specific'

            class Foo(object):
                pass

            @cherrypy.expose
            @cherrypy.config(**{'tools.expires.secs': Foo()})
            def wrongtype(self):
                cherrypy.response.headers[
                    'Etag'] = 'need_this_to_make_me_cacheable'
                return 'Woops'

        @cherrypy.config(**{
            'tools.gzip.mime_types': ['text/*', 'image/*'],
            'tools.caching.on': True,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
            'tools.staticdir.root': curdir
        })
        class GzipStaticCache(object):
            pass

        cherrypy.tree.mount(Root())
        cherrypy.tree.mount(UnCached(), '/expires')
        cherrypy.tree.mount(VaryHeaderCachingServer(), '/varying_headers')
        cherrypy.tree.mount(GzipStaticCache(), '/gzip_static_cache')
        cherrypy.config.update({'tools.gzip.on': True})

    def testCaching(self):
        elapsed = 0.0
        for trial in range(10):
            self.getPage('/')
            # The response should be the same every time,
            # except for the Age response header.
            self.assertBody('visit #1')
            if trial != 0:
                age = int(self.assertHeader('Age'))
                self.assert_(age >= elapsed)
                elapsed = age

        # POST, PUT, DELETE should not be cached.
        self.getPage('/', method='POST')
        self.assertBody('visit #2')
        # Because gzip is turned on, the Vary header should always Vary for
        # content-encoding
        self.assertHeader('Vary', 'Accept-Encoding')
        # The previous request should have invalidated the cache,
        # so this request will recalc the response.
        self.getPage('/', method='GET')
        self.assertBody('visit #3')
        # ...but this request should get the cached copy.
        self.getPage('/', method='GET')
        self.assertBody('visit #3')
        self.getPage('/', method='DELETE')
        self.assertBody('visit #4')

        # The previous request should have invalidated the cache,
        # so this request will recalc the response.
        self.getPage('/', method='GET', headers=[('Accept-Encoding', 'gzip')])
        self.assertHeader('Content-Encoding', 'gzip')
        self.assertHeader('Vary')
        self.assertEqual(
            cherrypy.lib.encoding.decompress(self.body), b'visit #5')

        # Now check that a second request gets the gzip header and gzipped body
        # This also tests a bug in 3.0 to 3.0.2 whereby the cached, gzipped
        # response body was being gzipped a second time.
        self.getPage('/', method='GET', headers=[('Accept-Encoding', 'gzip')])
        self.assertHeader('Content-Encoding', 'gzip')
        self.assertEqual(
            cherrypy.lib.encoding.decompress(self.body), b'visit #5')

        # Now check that a third request that doesn't accept gzip
        # skips the cache (because the 'Vary' header denies it).
        self.getPage('/', method='GET')
        self.assertNoHeader('Content-Encoding')
        self.assertBody('visit #6')

    def testVaryHeader(self):
        self.getPage('/varying_headers/')
        self.assertStatus('200 OK')
        self.assertHeaderItemValue('Vary', 'Our-Varying-Header')
        self.assertBody('visit #1')

        # Now check that different 'Vary'-fields don't evict each other.
        # This test creates 2 requests with different 'Our-Varying-Header'
        # and then tests if the first one still exists.
        self.getPage('/varying_headers/',
                     headers=[('Our-Varying-Header', 'request 2')])
        self.assertStatus('200 OK')
        self.assertBody('visit #2')

        self.getPage('/varying_headers/',
                     headers=[('Our-Varying-Header', 'request 2')])
        self.assertStatus('200 OK')
        self.assertBody('visit #2')

        self.getPage('/varying_headers/')
        self.assertStatus('200 OK')
        self.assertBody('visit #1')

    def testExpiresTool(self):
        # test setting an expires header
        self.getPage('/expires/specific')
        self.assertStatus('200 OK')
        self.assertHeader('Expires')

        # test exceptions for bad time values
        self.getPage('/expires/wrongtype')
        self.assertStatus(500)
        self.assertInBody('TypeError')

        # static content should not have "cache prevention" headers
        self.getPage('/expires/index.html')
        self.assertStatus('200 OK')
        self.assertNoHeader('Pragma')
        self.assertNoHeader('Cache-Control')
        self.assertHeader('Expires')

        # dynamic content that sets indicators should not have
        # "cache prevention" headers
        self.getPage('/expires/cacheable')
        self.assertStatus('200 OK')
        self.assertNoHeader('Pragma')
        self.assertNoHeader('Cache-Control')
        self.assertHeader('Expires')

        self.getPage('/expires/dynamic')
        self.assertBody('D-d-d-dynamic!')
        # the Cache-Control header should be untouched
        self.assertHeader('Cache-Control', 'private')
        self.assertHeader('Expires')

        # configure the tool to ignore indicators and replace existing headers
        self.getPage('/expires/force')
        self.assertStatus('200 OK')
        # This also gives us a chance to test 0 expiry with no other headers
        self.assertHeader('Pragma', 'no-cache')
        if cherrypy.server.protocol_version == 'HTTP/1.1':
            self.assertHeader('Cache-Control', 'no-cache, must-revalidate')
        self.assertHeader('Expires', 'Sun, 28 Jan 2007 00:00:00 GMT')

        # static content should now have "cache prevention" headers
        self.getPage('/expires/index.html')
        self.assertStatus('200 OK')
        self.assertHeader('Pragma', 'no-cache')
        if cherrypy.server.protocol_version == 'HTTP/1.1':
            self.assertHeader('Cache-Control', 'no-cache, must-revalidate')
        self.assertHeader('Expires', 'Sun, 28 Jan 2007 00:00:00 GMT')

        # the cacheable handler should now have "cache prevention" headers
        self.getPage('/expires/cacheable')
        self.assertStatus('200 OK')
        self.assertHeader('Pragma', 'no-cache')
        if cherrypy.server.protocol_version == 'HTTP/1.1':
            self.assertHeader('Cache-Control', 'no-cache, must-revalidate')
        self.assertHeader('Expires', 'Sun, 28 Jan 2007 00:00:00 GMT')

        self.getPage('/expires/dynamic')
        self.assertBody('D-d-d-dynamic!')
        # dynamic sets Cache-Control to private but it should  be
        # overwritten here ...
        self.assertHeader('Pragma', 'no-cache')
        if cherrypy.server.protocol_version == 'HTTP/1.1':
            self.assertHeader('Cache-Control', 'no-cache, must-revalidate')
        self.assertHeader('Expires', 'Sun, 28 Jan 2007 00:00:00 GMT')

    def _assert_resp_len_and_enc_for_gzip(self, uri):
        """
        Test that after querying gzipped content it's remains valid in
        cache and available non-gzipped as well.
        """
        ACCEPT_GZIP_HEADERS = [('Accept-Encoding', 'gzip')]
        content_len = None

        for _ in range(3):
            self.getPage(uri, method='GET', headers=ACCEPT_GZIP_HEADERS)

            if content_len is not None:
                # all requests should get the same length
                self.assertHeader('Content-Length', content_len)
                self.assertHeader('Content-Encoding', 'gzip')

            content_len = dict(self.headers)['Content-Length']

        # check that we can still get non-gzipped version
        self.getPage(uri, method='GET')
        self.assertNoHeader('Content-Encoding')
        # non-gzipped version should have a different content length
        self.assertNoHeaderItemValue('Content-Length', content_len)

    def testGzipStaticCache(self):
        """Test that cache and gzip tools play well together when both enabled.

        Ref GitHub issue #1190.
        """
        GZIP_STATIC_CACHE_TMPL = '/gzip_static_cache/{}'
        resource_files = ('index.html', 'dirback.jpg')

        for f in resource_files:
            uri = GZIP_STATIC_CACHE_TMPL.format(f)
            self._assert_resp_len_and_enc_for_gzip(uri)

    def testLastModified(self):
        self.getPage('/a.gif')
        self.assertStatus(200)
        self.assertBody(gif_bytes)
        lm1 = self.assertHeader('Last-Modified')

        # this request should get the cached copy.
        self.getPage('/a.gif')
        self.assertStatus(200)
        self.assertBody(gif_bytes)
        self.assertHeader('Age')
        lm2 = self.assertHeader('Last-Modified')
        self.assertEqual(lm1, lm2)

        # this request should match the cached copy, but raise 304.
        self.getPage('/a.gif', [('If-Modified-Since', lm1)])
        self.assertStatus(304)
        self.assertNoHeader('Last-Modified')
        if not getattr(cherrypy.server, 'using_apache', False):
            self.assertHeader('Age')

    @pytest.mark.xfail(reason='#1536')
    def test_antistampede(self):
        SECONDS = 4
        slow_url = '/long_process?seconds={SECONDS}'.format(**locals())
        # We MUST make an initial synchronous request in order to create the
        # AntiStampedeCache object, and populate its selecting_headers,
        # before the actual stampede.
        self.getPage(slow_url)
        self.assertBody('success!')
        path = urllib.parse.quote(slow_url, safe='')
        self.getPage('/clear_cache?path=' + path)
        self.assertStatus(200)

        start = datetime.datetime.now()

        def run():
            self.getPage(slow_url)
            # The response should be the same every time
            self.assertBody('success!')
        ts = [threading.Thread(target=run) for i in range(100)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        finish = datetime.datetime.now()
        # Allow for overhead, two seconds for slow hosts
        allowance = SECONDS + 2
        self.assertEqualDates(start, finish, seconds=allowance)

    def test_cache_control(self):
        self.getPage('/control')
        self.assertBody('visit #1')
        self.getPage('/control')
        self.assertBody('visit #1')

        self.getPage('/control', headers=[('Cache-Control', 'no-cache')])
        self.assertBody('visit #2')
        self.getPage('/control')
        self.assertBody('visit #2')

        self.getPage('/control', headers=[('Pragma', 'no-cache')])
        self.assertBody('visit #3')
        self.getPage('/control')
        self.assertBody('visit #3')

        time.sleep(1)
        self.getPage('/control', headers=[('Cache-Control', 'max-age=0')])
        self.assertBody('visit #4')
        self.getPage('/control')
        self.assertBody('visit #4')
