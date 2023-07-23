import os
import platform
import threading
import time
from http.client import HTTPConnection

from distutils.spawn import find_executable
import pytest
from path import Path
from more_itertools import consume
import portend

import cherrypy
from cherrypy._cpcompat import HTTPSConnection
from cherrypy.lib import sessions
from cherrypy.lib import reprconf
from cherrypy.lib.httputil import response_codes
from cherrypy.test import helper
from cherrypy import _json as json

localDir = Path(__file__).dirname()


def http_methods_allowed(methods=['GET', 'HEAD']):
    method = cherrypy.request.method.upper()
    if method not in methods:
        cherrypy.response.headers['Allow'] = ', '.join(methods)
        raise cherrypy.HTTPError(405)


cherrypy.tools.allow = cherrypy.Tool('on_start_resource', http_methods_allowed)


def setup_server():

    @cherrypy.config(**{
        'tools.sessions.on': True,
        'tools.sessions.storage_class': sessions.RamSession,
        'tools.sessions.storage_path': localDir,
        'tools.sessions.timeout': (1.0 / 60),
        'tools.sessions.clean_freq': (1.0 / 60),
    })
    class Root:

        @cherrypy.expose
        def clear(self):
            cherrypy.session.cache.clear()

        @cherrypy.expose
        @cherrypy.tools.json_out()
        def data(self):
            cherrypy.session['aha'] = 'foo'
            return cherrypy.session._data

        @cherrypy.expose
        def testGen(self):
            counter = cherrypy.session.get('counter', 0) + 1
            cherrypy.session['counter'] = counter
            yield str(counter)

        @cherrypy.expose
        def testStr(self):
            counter = cherrypy.session.get('counter', 0) + 1
            cherrypy.session['counter'] = counter
            return str(counter)

        @cherrypy.expose
        @cherrypy.config(**{'tools.sessions.on': False})
        def set_session_cls(self, new_cls_name):
            new_cls = reprconf.attributes(new_cls_name)
            cfg = {'tools.sessions.storage_class': new_cls}
            self.__class__._cp_config.update(cfg)
            if hasattr(cherrypy, 'session'):
                del cherrypy.session
            if new_cls.clean_thread:
                new_cls.clean_thread.stop()
                new_cls.clean_thread.unsubscribe()
                del new_cls.clean_thread

        @cherrypy.expose
        def index(self):
            sess = cherrypy.session
            c = sess.get('counter', 0) + 1
            time.sleep(0.01)
            sess['counter'] = c
            return str(c)

        @cherrypy.expose
        def keyin(self, key):
            return str(key in cherrypy.session)

        @cherrypy.expose
        def delete(self):
            cherrypy.session.delete()
            sessions.expire()
            return 'done'

        @cherrypy.expose
        def delkey(self, key):
            del cherrypy.session[key]
            return 'OK'

        @cherrypy.expose
        def redir_target(self):
            return self._cp_config['tools.sessions.storage_class'].__name__

        @cherrypy.expose
        def iredir(self):
            raise cherrypy.InternalRedirect('/redir_target')

        @cherrypy.expose
        @cherrypy.config(**{
            'tools.allow.on': True,
            'tools.allow.methods': ['GET'],
        })
        def restricted(self):
            return cherrypy.request.method

        @cherrypy.expose
        def regen(self):
            cherrypy.tools.sessions.regenerate()
            return 'logged in'

        @cherrypy.expose
        def length(self):
            return str(len(cherrypy.session))

        @cherrypy.expose
        @cherrypy.config(**{
            'tools.sessions.path': '/session_cookie',
            'tools.sessions.name': 'temp',
            'tools.sessions.persistent': False,
        })
        def session_cookie(self):
            # Must load() to start the clean thread.
            cherrypy.session.load()
            return cherrypy.session.id

    cherrypy.tree.mount(Root())


class SessionTest(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    @classmethod
    def teardown_class(cls):
        """Clean up sessions."""
        super(cls, cls).teardown_class()
        consume(
            file.remove_p()
            for file in localDir.listdir()
            if file.basename().startswith(
                sessions.FileSession.SESSION_PREFIX
            )
        )

    def test_0_Session(self):
        self.getPage('/set_session_cls/cherrypy.lib.sessions.RamSession')
        self.getPage('/clear')

        # Test that a normal request gets the same id in the cookies.
        # Note: this wouldn't work if /data didn't load the session.
        self.getPage('/data')
        assert self.body == b'{"aha": "foo"}'
        c = self.cookies[0]
        self.getPage('/data', self.cookies)
        self.cookies[0] == c

        self.getPage('/testStr')
        assert self.body == b'1'
        cookie_parts = dict([p.strip().split('=')
                             for p in self.cookies[0][1].split(';')])
        # Assert there is an 'expires' param
        expected_cookie_keys = {'session_id', 'expires', 'Path', 'Max-Age'}
        assert set(cookie_parts.keys()) == expected_cookie_keys
        self.getPage('/testGen', self.cookies)
        assert self.body == b'2'
        self.getPage('/testStr', self.cookies)
        assert self.body == b'3'
        self.getPage('/data', self.cookies)
        expected_data = {'counter': 3, 'aha': 'foo'}
        assert json.decode(self.body.decode('utf-8')) == expected_data
        self.getPage('/length', self.cookies)
        assert self.body == b'2'
        self.getPage('/delkey?key=counter', self.cookies)
        assert self.status_code == 200

        self.getPage('/set_session_cls/cherrypy.lib.sessions.FileSession')
        self.getPage('/testStr')
        assert self.body == b'1'
        self.getPage('/testGen', self.cookies)
        assert self.body == b'2'
        self.getPage('/testStr', self.cookies)
        assert self.body == b'3'
        self.getPage('/delkey?key=counter', self.cookies)
        assert self.status_code == 200

        # Wait for the session.timeout (1 second)
        time.sleep(2)
        self.getPage('/')
        assert self.body == b'1'
        self.getPage('/length', self.cookies)
        assert self.body == b'1'

        # Test session __contains__
        self.getPage('/keyin?key=counter', self.cookies)
        assert self.body == b'True'
        cookieset1 = self.cookies

        # Make a new session and test __len__ again
        self.getPage('/')
        self.getPage('/length', self.cookies)
        assert self.body == b'2'

        # Test session delete
        self.getPage('/delete', self.cookies)
        assert self.body == b'done'
        self.getPage('/delete', cookieset1)
        assert self.body == b'done'

        def f():
            return [
                x
                for x in os.listdir(localDir)
                if x.startswith('session-') and not x.endswith('.lock')
            ]
        assert f() == []

        # Wait for the cleanup thread to delete remaining session files
        self.getPage('/')
        assert f() != []
        time.sleep(2)
        assert f() == []

    def test_1_Ram_Concurrency(self):
        self.getPage('/set_session_cls/cherrypy.lib.sessions.RamSession')
        self._test_Concurrency()

    def test_2_File_Concurrency(self):
        self.getPage('/set_session_cls/cherrypy.lib.sessions.FileSession')
        self._test_Concurrency()

    def _test_Concurrency(self):
        client_thread_count = 5
        request_count = 30

        # Get initial cookie
        self.getPage('/')
        assert self.body == b'1'
        cookies = self.cookies

        data_dict = {}
        errors = []

        def request(index):
            if self.scheme == 'https':
                c = HTTPSConnection('%s:%s' % (self.interface(), self.PORT))
            else:
                c = HTTPConnection('%s:%s' % (self.interface(), self.PORT))
            for i in range(request_count):
                c.putrequest('GET', '/')
                for k, v in cookies:
                    c.putheader(k, v)
                c.endheaders()
                response = c.getresponse()
                body = response.read()
                if response.status != 200 or not body.isdigit():
                    errors.append((response.status, body))
                else:
                    data_dict[index] = max(data_dict[index], int(body))
                # Uncomment the following line to prove threads overlap.
                # sys.stdout.write("%d " % index)

        # Start <request_count> requests from each of
        # <client_thread_count> concurrent clients
        ts = []
        for c in range(client_thread_count):
            data_dict[c] = 0
            t = threading.Thread(target=request, args=(c,))
            ts.append(t)
            t.start()

        for t in ts:
            t.join()

        hitcount = max(data_dict.values())
        expected = 1 + (client_thread_count * request_count)

        for e in errors:
            print(e)
        assert len(errors) == 0
        assert hitcount == expected

    def test_3_Redirect(self):
        # Start a new session
        self.getPage('/testStr')
        self.getPage('/iredir', self.cookies)
        assert self.body == b'FileSession'

    def test_4_File_deletion(self):
        # Start a new session
        self.getPage('/testStr')
        # Delete the session file manually and retry.
        id = self.cookies[0][1].split(';', 1)[0].split('=', 1)[1]
        path = os.path.join(localDir, 'session-' + id)
        os.unlink(path)
        self.getPage('/testStr', self.cookies)

    def test_5_Error_paths(self):
        self.getPage('/unknown/page')
        self.assertErrorPage(404, "The path '/unknown/page' was not found.")

        # Note: this path is *not* the same as above. The above
        # takes a normal route through the session code; this one
        # skips the session code's before_handler and only calls
        # before_finalize (save) and on_end (close). So the session
        # code has to survive calling save/close without init.
        self.getPage('/restricted', self.cookies, method='POST')
        self.assertErrorPage(405, response_codes[405][1])

    def test_6_regenerate(self):
        self.getPage('/testStr')
        # grab the cookie ID
        id1 = self.cookies[0][1].split(';', 1)[0].split('=', 1)[1]
        self.getPage('/regen')
        assert self.body == b'logged in'
        id2 = self.cookies[0][1].split(';', 1)[0].split('=', 1)[1]
        assert id1 != id2

        self.getPage('/testStr')
        # grab the cookie ID
        id1 = self.cookies[0][1].split(';', 1)[0].split('=', 1)[1]
        self.getPage('/testStr',
                     headers=[
                         ('Cookie',
                          'session_id=maliciousid; '
                          'expires=Sat, 27 Oct 2017 04:18:28 GMT; Path=/;')])
        id2 = self.cookies[0][1].split(';', 1)[0].split('=', 1)[1]
        assert id1 != id2
        assert id2 != 'maliciousid'

    def test_7_session_cookies(self):
        self.getPage('/set_session_cls/cherrypy.lib.sessions.RamSession')
        self.getPage('/clear')
        self.getPage('/session_cookie')
        # grab the cookie ID
        cookie_parts = dict([p.strip().split('=')
                            for p in self.cookies[0][1].split(';')])
        # Assert there is no 'expires' param
        assert set(cookie_parts.keys()) == {'temp', 'Path'}
        id1 = cookie_parts['temp']
        assert list(sessions.RamSession.cache) == [id1]

        # Send another request in the same "browser session".
        self.getPage('/session_cookie', self.cookies)
        cookie_parts = dict([p.strip().split('=')
                            for p in self.cookies[0][1].split(';')])
        # Assert there is no 'expires' param
        assert set(cookie_parts.keys()) == {'temp', 'Path'}
        assert self.body.decode('utf-8') == id1
        assert list(sessions.RamSession.cache) == [id1]

        # Simulate a browser close by just not sending the cookies
        self.getPage('/session_cookie')
        # grab the cookie ID
        cookie_parts = dict([p.strip().split('=')
                            for p in self.cookies[0][1].split(';')])
        # Assert there is no 'expires' param
        assert set(cookie_parts.keys()) == {'temp', 'Path'}
        # Assert a new id has been generated...
        id2 = cookie_parts['temp']
        assert id1 != id2
        assert set(sessions.RamSession.cache.keys()) == {id1, id2}

        # Wait for the session.timeout on both sessions
        time.sleep(2.5)
        cache = list(sessions.RamSession.cache)
        if cache:
            if cache == [id2]:
                self.fail('The second session did not time out.')
            else:
                self.fail('Unknown session id in cache: %r', cache)

    def test_8_Ram_Cleanup(self):
        def lock():
            s1 = sessions.RamSession()
            s1.acquire_lock()
            time.sleep(1)
            s1.release_lock()

        t = threading.Thread(target=lock)
        t.start()
        start = time.time()
        while not sessions.RamSession.locks and time.time() - start < 5:
            time.sleep(0.01)
        assert len(sessions.RamSession.locks) == 1, 'Lock not acquired'
        s2 = sessions.RamSession()
        s2.clean_up()
        msg = 'Clean up should not remove active lock'
        assert len(sessions.RamSession.locks) == 1, msg
        t.join()


def is_memcached_present():
    executable = find_executable('memcached')
    return bool(executable)


@pytest.fixture(scope='session')
def memcached_server_present():
    is_memcached_present() or pytest.skip('memcached not available')


@pytest.fixture()
def memcached_client_present():
    pytest.importorskip('memcache')


@pytest.fixture(scope='session')
def memcached_instance(request, watcher_getter, memcached_server_present):
    """
    Start up an instance of memcached.
    """

    port = portend.find_available_local_port()

    def is_occupied():
        try:
            portend.Checker().assert_free('localhost', port)
        except Exception:
            return True
        return False

    proc = watcher_getter(
        name='memcached',
        arguments=['-p', str(port)],
        checker=is_occupied,
        request=request,
    )
    return locals()


@pytest.fixture
def memcached_configured(
    memcached_instance, monkeypatch,
    memcached_client_present,
):
    server = 'localhost:{port}'.format_map(memcached_instance)
    monkeypatch.setattr(
        sessions.MemcachedSession,
        'servers',
        [server],
    )


@pytest.mark.skipif(
    platform.system() == 'Windows',
    reason='pytest-services helper does not work under Windows',
)
@pytest.mark.usefixtures('memcached_configured')
class MemcachedSessionTest(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def test_0_Session(self):
        self.getPage(
            '/set_session_cls/cherrypy.lib.sessions.MemcachedSession'
        )

        self.getPage('/testStr')
        assert self.body == b'1'
        self.getPage('/testGen', self.cookies)
        assert self.body == b'2'
        self.getPage('/testStr', self.cookies)
        assert self.body == b'3'
        self.getPage('/length', self.cookies)
        self.assertErrorPage(500)
        assert b'NotImplementedError' in self.body
        self.getPage('/delkey?key=counter', self.cookies)
        assert self.status_code == 200

        # Wait for the session.timeout (1 second)
        time.sleep(1.25)
        self.getPage('/')
        assert self.body == b'1'

        # Test session __contains__
        self.getPage('/keyin?key=counter', self.cookies)
        assert self.body == b'True'

        # Test session delete
        self.getPage('/delete', self.cookies)
        assert self.body == b'done'

    def test_1_Concurrency(self):
        client_thread_count = 5
        request_count = 30

        # Get initial cookie
        self.getPage('/')
        assert self.body == b'1'
        cookies = self.cookies

        data_dict = {}

        def request(index):
            for i in range(request_count):
                self.getPage('/', cookies)
                # Uncomment the following line to prove threads overlap.
                # sys.stdout.write("%d " % index)
            if not self.body.isdigit():
                self.fail(self.body)
            data_dict[index] = int(self.body)

        # Start <request_count> concurrent requests from
        # each of <client_thread_count> clients
        ts = []
        for c in range(client_thread_count):
            data_dict[c] = 0
            t = threading.Thread(target=request, args=(c,))
            ts.append(t)
            t.start()

        for t in ts:
            t.join()

        hitcount = max(data_dict.values())
        expected = 1 + (client_thread_count * request_count)
        assert hitcount == expected

    def test_3_Redirect(self):
        # Start a new session
        self.getPage('/testStr')
        self.getPage('/iredir', self.cookies)
        assert self.body == b'MemcachedSession'

    def test_5_Error_paths(self):
        self.getPage('/unknown/page')
        self.assertErrorPage(
            404, "The path '/unknown/page' was not found.")

        # Note: this path is *not* the same as above. The above
        # takes a normal route through the session code; this one
        # skips the session code's before_handler and only calls
        # before_finalize (save) and on_end (close). So the session
        # code has to survive calling save/close without init.
        self.getPage('/restricted', self.cookies, method='POST')
        self.assertErrorPage(405, response_codes[405][1])
