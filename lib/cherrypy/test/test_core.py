# coding: utf-8

"""Basic tests for the CherryPy core: request handling."""

import os
import sys
import types

import six

import cherrypy
from cherrypy._cpcompat import ntou
from cherrypy import _cptools, tools
from cherrypy.lib import httputil, static

from cherrypy.test._test_decorators import ExposeExamples
from cherrypy.test import helper


localDir = os.path.dirname(__file__)
favicon_path = os.path.join(os.getcwd(), localDir, '../favicon.ico')

#                             Client-side code                             #


class CoreRequestHandlingTest(helper.CPWebCase):

    @staticmethod
    def setup_server():
        class Root:

            @cherrypy.expose
            def index(self):
                return 'hello'

            favicon_ico = tools.staticfile.handler(filename=favicon_path)

            @cherrypy.expose
            def defct(self, newct):
                newct = 'text/%s' % newct
                cherrypy.config.update({'tools.response_headers.on': True,
                                        'tools.response_headers.headers':
                                        [('Content-Type', newct)]})

            @cherrypy.expose
            def baseurl(self, path_info, relative=None):
                return cherrypy.url(path_info, relative=bool(relative))

        root = Root()
        root.expose_dec = ExposeExamples()

        class TestType(type):

            """Metaclass which automatically exposes all functions in each
            subclass, and adds an instance of the subclass as an attribute
            of root.
            """
            def __init__(cls, name, bases, dct):
                type.__init__(cls, name, bases, dct)
                for value in six.itervalues(dct):
                    if isinstance(value, types.FunctionType):
                        value.exposed = True
                setattr(root, name.lower(), cls())
        Test = TestType('Test', (object, ), {})

        @cherrypy.config(**{'tools.trailing_slash.on': False})
        class URL(Test):

            def index(self, path_info, relative=None):
                if relative != 'server':
                    relative = bool(relative)
                return cherrypy.url(path_info, relative=relative)

            def leaf(self, path_info, relative=None):
                if relative != 'server':
                    relative = bool(relative)
                return cherrypy.url(path_info, relative=relative)

            def qs(self, qs):
                return cherrypy.url(qs=qs)

        def log_status():
            Status.statuses.append(cherrypy.response.status)
        cherrypy.tools.log_status = cherrypy.Tool(
            'on_end_resource', log_status)

        class Status(Test):

            def index(self):
                return 'normal'

            def blank(self):
                cherrypy.response.status = ''

            # According to RFC 2616, new status codes are OK as long as they
            # are between 100 and 599.

            # Here is an illegal code...
            def illegal(self):
                cherrypy.response.status = 781
                return 'oops'

            # ...and here is an unknown but legal code.
            def unknown(self):
                cherrypy.response.status = '431 My custom error'
                return 'funky'

            # Non-numeric code
            def bad(self):
                cherrypy.response.status = 'error'
                return 'bad news'

            statuses = []

            @cherrypy.config(**{'tools.log_status.on': True})
            def on_end_resource_stage(self):
                return repr(self.statuses)

        class Redirect(Test):

            @cherrypy.config(**{
                'tools.err_redirect.on': True,
                'tools.err_redirect.url': '/errpage',
                'tools.err_redirect.internal': False,
            })
            class Error:
                @cherrypy.expose
                def index(self):
                    raise NameError('redirect_test')

            error = Error()

            def index(self):
                return 'child'

            def custom(self, url, code):
                raise cherrypy.HTTPRedirect(url, code)

            @cherrypy.config(**{'tools.trailing_slash.extra': True})
            def by_code(self, code):
                raise cherrypy.HTTPRedirect('somewhere%20else', code)

            def nomodify(self):
                raise cherrypy.HTTPRedirect('', 304)

            def proxy(self):
                raise cherrypy.HTTPRedirect('proxy', 305)

            def stringify(self):
                return str(cherrypy.HTTPRedirect('/'))

            def fragment(self, frag):
                raise cherrypy.HTTPRedirect('/some/url#%s' % frag)

            def url_with_quote(self):
                raise cherrypy.HTTPRedirect("/some\"url/that'we/want")

            def url_with_xss(self):
                raise cherrypy.HTTPRedirect(
                    "/some<script>alert(1);</script>url/that'we/want")

            def url_with_unicode(self):
                raise cherrypy.HTTPRedirect(ntou('тест', 'utf-8'))

        def login_redir():
            if not getattr(cherrypy.request, 'login', None):
                raise cherrypy.InternalRedirect('/internalredirect/login')
        tools.login_redir = _cptools.Tool('before_handler', login_redir)

        def redir_custom():
            raise cherrypy.InternalRedirect('/internalredirect/custom_err')

        class InternalRedirect(Test):

            def index(self):
                raise cherrypy.InternalRedirect('/')

            @cherrypy.expose
            @cherrypy.config(**{'hooks.before_error_response': redir_custom})
            def choke(self):
                return 3 / 0

            def relative(self, a, b):
                raise cherrypy.InternalRedirect('cousin?t=6')

            def cousin(self, t):
                assert cherrypy.request.prev.closed
                return cherrypy.request.prev.query_string

            def petshop(self, user_id):
                if user_id == 'parrot':
                    # Trade it for a slug when redirecting
                    raise cherrypy.InternalRedirect(
                        '/image/getImagesByUser?user_id=slug')
                elif user_id == 'terrier':
                    # Trade it for a fish when redirecting
                    raise cherrypy.InternalRedirect(
                        '/image/getImagesByUser?user_id=fish')
                else:
                    # This should pass the user_id through to getImagesByUser
                    raise cherrypy.InternalRedirect(
                        '/image/getImagesByUser?user_id=%s' % str(user_id))

            # We support Python 2.3, but the @-deco syntax would look like
            # this:
            # @tools.login_redir()
            def secure(self):
                return 'Welcome!'
            secure = tools.login_redir()(secure)
            # Since calling the tool returns the same function you pass in,
            # you could skip binding the return value, and just write:
            # tools.login_redir()(secure)

            def login(self):
                return 'Please log in'

            def custom_err(self):
                return 'Something went horribly wrong.'

            @cherrypy.config(**{'hooks.before_request_body': redir_custom})
            def early_ir(self, arg):
                return 'whatever'

        class Image(Test):

            def getImagesByUser(self, user_id):
                return '0 images for %s' % user_id

        class Flatten(Test):

            def as_string(self):
                return 'content'

            def as_list(self):
                return ['con', 'tent']

            def as_yield(self):
                yield b'content'

            @cherrypy.config(**{'tools.flatten.on': True})
            def as_dblyield(self):
                yield self.as_yield()

            def as_refyield(self):
                for chunk in self.as_yield():
                    yield chunk

        class Ranges(Test):

            def get_ranges(self, bytes):
                return repr(httputil.get_ranges('bytes=%s' % bytes, 8))

            def slice_file(self):
                path = os.path.join(os.getcwd(), os.path.dirname(__file__))
                return static.serve_file(
                    os.path.join(path, 'static/index.html'))

        class Cookies(Test):

            def single(self, name):
                cookie = cherrypy.request.cookie[name]
                # Python2's SimpleCookie.__setitem__ won't take unicode keys.
                cherrypy.response.cookie[str(name)] = cookie.value

            def multiple(self, names):
                list(map(self.single, names))

        def append_headers(header_list, debug=False):
            if debug:
                cherrypy.log(
                    'Extending response headers with %s' % repr(header_list),
                    'TOOLS.APPEND_HEADERS')
            cherrypy.serving.response.header_list.extend(header_list)
        cherrypy.tools.append_headers = cherrypy.Tool(
            'on_end_resource', append_headers)

        class MultiHeader(Test):

            def header_list(self):
                pass
            header_list = cherrypy.tools.append_headers(header_list=[
                (b'WWW-Authenticate', b'Negotiate'),
                (b'WWW-Authenticate', b'Basic realm="foo"'),
            ])(header_list)

            def commas(self):
                cherrypy.response.headers[
                    'WWW-Authenticate'] = 'Negotiate,Basic realm="foo"'

        cherrypy.tree.mount(root)

    def testStatus(self):
        self.getPage('/status/')
        self.assertBody('normal')
        self.assertStatus(200)

        self.getPage('/status/blank')
        self.assertBody('')
        self.assertStatus(200)

        self.getPage('/status/illegal')
        self.assertStatus(500)
        msg = 'Illegal response status from server (781 is out of range).'
        self.assertErrorPage(500, msg)

        if not getattr(cherrypy.server, 'using_apache', False):
            self.getPage('/status/unknown')
            self.assertBody('funky')
            self.assertStatus(431)

        self.getPage('/status/bad')
        self.assertStatus(500)
        msg = "Illegal response status from server ('error' is non-numeric)."
        self.assertErrorPage(500, msg)

    def test_on_end_resource_status(self):
        self.getPage('/status/on_end_resource_stage')
        self.assertBody('[]')
        self.getPage('/status/on_end_resource_stage')
        self.assertBody(repr(['200 OK']))

    def testSlashes(self):
        # Test that requests for index methods without a trailing slash
        # get redirected to the same URI path with a trailing slash.
        # Make sure GET params are preserved.
        self.getPage('/redirect?id=3')
        self.assertStatus(301)
        self.assertMatchesBody(
            '<a href=([\'"])%s/redirect/[?]id=3\\1>'
            '%s/redirect/[?]id=3</a>' % (self.base(), self.base())
        )

        if self.prefix():
            # Corner case: the "trailing slash" redirect could be tricky if
            # we're using a virtual root and the URI is "/vroot" (no slash).
            self.getPage('')
            self.assertStatus(301)
            self.assertMatchesBody("<a href=(['\"])%s/\\1>%s/</a>" %
                                   (self.base(), self.base()))

        # Test that requests for NON-index methods WITH a trailing slash
        # get redirected to the same URI path WITHOUT a trailing slash.
        # Make sure GET params are preserved.
        self.getPage('/redirect/by_code/?code=307')
        self.assertStatus(301)
        self.assertMatchesBody(
            "<a href=(['\"])%s/redirect/by_code[?]code=307\\1>"
            '%s/redirect/by_code[?]code=307</a>'
            % (self.base(), self.base())
        )

        # If the trailing_slash tool is off, CP should just continue
        # as if the slashes were correct. But it needs some help
        # inside cherrypy.url to form correct output.
        self.getPage('/url?path_info=page1')
        self.assertBody('%s/url/page1' % self.base())
        self.getPage('/url/leaf/?path_info=page1')
        self.assertBody('%s/url/page1' % self.base())

    def testRedirect(self):
        self.getPage('/redirect/')
        self.assertBody('child')
        self.assertStatus(200)

        self.getPage('/redirect/by_code?code=300')
        self.assertMatchesBody(
            r"<a href=(['\"])(.*)somewhere%20else\1>\2somewhere%20else</a>")
        self.assertStatus(300)

        self.getPage('/redirect/by_code?code=301')
        self.assertMatchesBody(
            r"<a href=(['\"])(.*)somewhere%20else\1>\2somewhere%20else</a>")
        self.assertStatus(301)

        self.getPage('/redirect/by_code?code=302')
        self.assertMatchesBody(
            r"<a href=(['\"])(.*)somewhere%20else\1>\2somewhere%20else</a>")
        self.assertStatus(302)

        self.getPage('/redirect/by_code?code=303')
        self.assertMatchesBody(
            r"<a href=(['\"])(.*)somewhere%20else\1>\2somewhere%20else</a>")
        self.assertStatus(303)

        self.getPage('/redirect/by_code?code=307')
        self.assertMatchesBody(
            r"<a href=(['\"])(.*)somewhere%20else\1>\2somewhere%20else</a>")
        self.assertStatus(307)

        self.getPage('/redirect/nomodify')
        self.assertBody('')
        self.assertStatus(304)

        self.getPage('/redirect/proxy')
        self.assertBody('')
        self.assertStatus(305)

        # HTTPRedirect on error
        self.getPage('/redirect/error/')
        self.assertStatus(('302 Found', '303 See Other'))
        self.assertInBody('/errpage')

        # Make sure str(HTTPRedirect()) works.
        self.getPage('/redirect/stringify', protocol='HTTP/1.0')
        self.assertStatus(200)
        self.assertBody("(['%s/'], 302)" % self.base())
        if cherrypy.server.protocol_version == 'HTTP/1.1':
            self.getPage('/redirect/stringify', protocol='HTTP/1.1')
            self.assertStatus(200)
            self.assertBody("(['%s/'], 303)" % self.base())

        # check that #fragments are handled properly
        # http://skrb.org/ietf/http_errata.html#location-fragments
        frag = 'foo'
        self.getPage('/redirect/fragment/%s' % frag)
        self.assertMatchesBody(
            r"<a href=(['\"])(.*)\/some\/url\#%s\1>\2\/some\/url\#%s</a>" % (
                frag, frag))
        loc = self.assertHeader('Location')
        assert loc.endswith('#%s' % frag)
        self.assertStatus(('302 Found', '303 See Other'))

        # check injection protection
        # See https://github.com/cherrypy/cherrypy/issues/1003
        self.getPage(
            '/redirect/custom?'
            'code=303&url=/foobar/%0d%0aSet-Cookie:%20somecookie=someval')
        self.assertStatus(303)
        loc = self.assertHeader('Location')
        assert 'Set-Cookie' in loc
        self.assertNoHeader('Set-Cookie')

        def assertValidXHTML():
            from xml.etree import ElementTree
            try:
                ElementTree.fromstring(
                    '<html><body>%s</body></html>' % self.body,
                )
            except ElementTree.ParseError:
                self._handlewebError(
                    'automatically generated redirect did not '
                    'generate well-formed html',
                )

        # check redirects to URLs generated valid HTML - we check this
        # by seeing if it appears as valid XHTML.
        self.getPage('/redirect/by_code?code=303')
        self.assertStatus(303)
        assertValidXHTML()

        # do the same with a url containing quote characters.
        self.getPage('/redirect/url_with_quote')
        self.assertStatus(303)
        assertValidXHTML()

    def test_redirect_with_xss(self):
        """A redirect to a URL with HTML injected should result
        in page contents escaped."""
        self.getPage('/redirect/url_with_xss')
        self.assertStatus(303)
        assert b'<script>' not in self.body
        assert b'&lt;script&gt;' in self.body

    def test_redirect_with_unicode(self):
        """
        A redirect to a URL with Unicode should return a Location
        header containing that Unicode URL.
        """
        # test disabled due to #1440
        return
        self.getPage('/redirect/url_with_unicode')
        self.assertStatus(303)
        loc = self.assertHeader('Location')
        assert ntou('тест', encoding='utf-8') in loc

    def test_InternalRedirect(self):
        # InternalRedirect
        self.getPage('/internalredirect/')
        self.assertBody('hello')
        self.assertStatus(200)

        # Test passthrough
        self.getPage(
            '/internalredirect/petshop?user_id=Sir-not-appearing-in-this-film')
        self.assertBody('0 images for Sir-not-appearing-in-this-film')
        self.assertStatus(200)

        # Test args
        self.getPage('/internalredirect/petshop?user_id=parrot')
        self.assertBody('0 images for slug')
        self.assertStatus(200)

        # Test POST
        self.getPage('/internalredirect/petshop', method='POST',
                     body='user_id=terrier')
        self.assertBody('0 images for fish')
        self.assertStatus(200)

        # Test ir before body read
        self.getPage('/internalredirect/early_ir', method='POST',
                     body='arg=aha!')
        self.assertBody('Something went horribly wrong.')
        self.assertStatus(200)

        self.getPage('/internalredirect/secure')
        self.assertBody('Please log in')
        self.assertStatus(200)

        # Relative path in InternalRedirect.
        # Also tests request.prev.
        self.getPage('/internalredirect/relative?a=3&b=5')
        self.assertBody('a=3&b=5')
        self.assertStatus(200)

        # InternalRedirect on error
        self.getPage('/internalredirect/choke')
        self.assertStatus(200)
        self.assertBody('Something went horribly wrong.')

    def testFlatten(self):
        for url in ['/flatten/as_string', '/flatten/as_list',
                    '/flatten/as_yield', '/flatten/as_dblyield',
                    '/flatten/as_refyield']:
            self.getPage(url)
            self.assertBody('content')

    def testRanges(self):
        self.getPage('/ranges/get_ranges?bytes=3-6')
        self.assertBody('[(3, 7)]')

        # Test multiple ranges and a suffix-byte-range-spec, for good measure.
        self.getPage('/ranges/get_ranges?bytes=2-4,-1')
        self.assertBody('[(2, 5), (7, 8)]')

        # Test a suffix-byte-range longer than the content
        # length. Note that in this test, the content length
        # is 8 bytes.
        self.getPage('/ranges/get_ranges?bytes=-100')
        self.assertBody('[(0, 8)]')

        # Get a partial file.
        if cherrypy.server.protocol_version == 'HTTP/1.1':
            self.getPage('/ranges/slice_file', [('Range', 'bytes=2-5')])
            self.assertStatus(206)
            self.assertHeader('Content-Type', 'text/html;charset=utf-8')
            self.assertHeader('Content-Range', 'bytes 2-5/14')
            self.assertBody('llo,')

            # What happens with overlapping ranges (and out of order, too)?
            self.getPage('/ranges/slice_file', [('Range', 'bytes=4-6,2-5')])
            self.assertStatus(206)
            ct = self.assertHeader('Content-Type')
            expected_type = 'multipart/byteranges; boundary='
            self.assert_(ct.startswith(expected_type))
            boundary = ct[len(expected_type):]
            expected_body = ('\r\n--%s\r\n'
                             'Content-type: text/html\r\n'
                             'Content-range: bytes 4-6/14\r\n'
                             '\r\n'
                             'o, \r\n'
                             '--%s\r\n'
                             'Content-type: text/html\r\n'
                             'Content-range: bytes 2-5/14\r\n'
                             '\r\n'
                             'llo,\r\n'
                             '--%s--\r\n' % (boundary, boundary, boundary))
            self.assertBody(expected_body)
            self.assertHeader('Content-Length')

            # Test "416 Requested Range Not Satisfiable"
            self.getPage('/ranges/slice_file', [('Range', 'bytes=2300-2900')])
            self.assertStatus(416)
            # "When this status code is returned for a byte-range request,
            # the response SHOULD include a Content-Range entity-header
            # field specifying the current length of the selected resource"
            self.assertHeader('Content-Range', 'bytes */14')
        elif cherrypy.server.protocol_version == 'HTTP/1.0':
            # Test Range behavior with HTTP/1.0 request
            self.getPage('/ranges/slice_file', [('Range', 'bytes=2-5')])
            self.assertStatus(200)
            self.assertBody('Hello, world\r\n')

    def testFavicon(self):
        # favicon.ico is served by staticfile.
        icofilename = os.path.join(localDir, '../favicon.ico')
        icofile = open(icofilename, 'rb')
        data = icofile.read()
        icofile.close()

        self.getPage('/favicon.ico')
        self.assertBody(data)

    def skip_if_bad_cookies(self):
        """
        cookies module fails to reject invalid cookies
        https://github.com/cherrypy/cherrypy/issues/1405
        """
        cookies = sys.modules.get('http.cookies')
        _is_legal_key = getattr(cookies, '_is_legal_key', lambda x: False)
        if not _is_legal_key(','):
            return
        issue = 'http://bugs.python.org/issue26302'
        tmpl = 'Broken cookies module ({issue})'
        self.skip(tmpl.format(**locals()))

    def testCookies(self):
        self.skip_if_bad_cookies()

        self.getPage('/cookies/single?name=First',
                     [('Cookie', 'First=Dinsdale;')])
        self.assertHeader('Set-Cookie', 'First=Dinsdale')

        self.getPage('/cookies/multiple?names=First&names=Last',
                     [('Cookie', 'First=Dinsdale; Last=Piranha;'),
                      ])
        self.assertHeader('Set-Cookie', 'First=Dinsdale')
        self.assertHeader('Set-Cookie', 'Last=Piranha')

        self.getPage('/cookies/single?name=Something-With%2CComma',
                     [('Cookie', 'Something-With,Comma=some-value')])
        self.assertStatus(400)

    def testDefaultContentType(self):
        self.getPage('/')
        self.assertHeader('Content-Type', 'text/html;charset=utf-8')
        self.getPage('/defct/plain')
        self.getPage('/')
        self.assertHeader('Content-Type', 'text/plain;charset=utf-8')
        self.getPage('/defct/html')

    def test_multiple_headers(self):
        self.getPage('/multiheader/header_list')
        self.assertEqual(
            [(k, v) for k, v in self.headers if k == 'WWW-Authenticate'],
            [('WWW-Authenticate', 'Negotiate'),
             ('WWW-Authenticate', 'Basic realm="foo"'),
             ])
        self.getPage('/multiheader/commas')
        self.assertHeader('WWW-Authenticate', 'Negotiate,Basic realm="foo"')

    def test_cherrypy_url(self):
        # Input relative to current
        self.getPage('/url/leaf?path_info=page1')
        self.assertBody('%s/url/page1' % self.base())
        self.getPage('/url/?path_info=page1')
        self.assertBody('%s/url/page1' % self.base())
        # Other host header
        host = 'www.mydomain.example'
        self.getPage('/url/leaf?path_info=page1',
                     headers=[('Host', host)])
        self.assertBody('%s://%s/url/page1' % (self.scheme, host))

        # Input is 'absolute'; that is, relative to script_name
        self.getPage('/url/leaf?path_info=/page1')
        self.assertBody('%s/page1' % self.base())
        self.getPage('/url/?path_info=/page1')
        self.assertBody('%s/page1' % self.base())

        # Single dots
        self.getPage('/url/leaf?path_info=./page1')
        self.assertBody('%s/url/page1' % self.base())
        self.getPage('/url/leaf?path_info=other/./page1')
        self.assertBody('%s/url/other/page1' % self.base())
        self.getPage('/url/?path_info=/other/./page1')
        self.assertBody('%s/other/page1' % self.base())
        self.getPage('/url/?path_info=/other/././././page1')
        self.assertBody('%s/other/page1' % self.base())

        # Double dots
        self.getPage('/url/leaf?path_info=../page1')
        self.assertBody('%s/page1' % self.base())
        self.getPage('/url/leaf?path_info=other/../page1')
        self.assertBody('%s/url/page1' % self.base())
        self.getPage('/url/leaf?path_info=/other/../page1')
        self.assertBody('%s/page1' % self.base())
        self.getPage('/url/leaf?path_info=/other/../../../page1')
        self.assertBody('%s/page1' % self.base())
        self.getPage('/url/leaf?path_info=/other/../../../../../page1')
        self.assertBody('%s/page1' % self.base())

        # qs param is not normalized as a path
        self.getPage('/url/qs?qs=/other')
        self.assertBody('%s/url/qs?/other' % self.base())
        self.getPage('/url/qs?qs=/other/../page1')
        self.assertBody('%s/url/qs?/other/../page1' % self.base())
        self.getPage('/url/qs?qs=../page1')
        self.assertBody('%s/url/qs?../page1' % self.base())
        self.getPage('/url/qs?qs=../../page1')
        self.assertBody('%s/url/qs?../../page1' % self.base())

        # Output relative to current path or script_name
        self.getPage('/url/?path_info=page1&relative=True')
        self.assertBody('page1')
        self.getPage('/url/leaf?path_info=/page1&relative=True')
        self.assertBody('../page1')
        self.getPage('/url/leaf?path_info=page1&relative=True')
        self.assertBody('page1')
        self.getPage('/url/leaf?path_info=leaf/page1&relative=True')
        self.assertBody('leaf/page1')
        self.getPage('/url/leaf?path_info=../page1&relative=True')
        self.assertBody('../page1')
        self.getPage('/url/?path_info=other/../page1&relative=True')
        self.assertBody('page1')

        # Output relative to /
        self.getPage('/baseurl?path_info=ab&relative=True')
        self.assertBody('ab')
        # Output relative to /
        self.getPage('/baseurl?path_info=/ab&relative=True')
        self.assertBody('ab')

        # absolute-path references ("server-relative")
        # Input relative to current
        self.getPage('/url/leaf?path_info=page1&relative=server')
        self.assertBody('/url/page1')
        self.getPage('/url/?path_info=page1&relative=server')
        self.assertBody('/url/page1')
        # Input is 'absolute'; that is, relative to script_name
        self.getPage('/url/leaf?path_info=/page1&relative=server')
        self.assertBody('/page1')
        self.getPage('/url/?path_info=/page1&relative=server')
        self.assertBody('/page1')

    def test_expose_decorator(self):
        # Test @expose
        self.getPage('/expose_dec/no_call')
        self.assertStatus(200)
        self.assertBody('Mr E. R. Bradshaw')

        # Test @expose()
        self.getPage('/expose_dec/call_empty')
        self.assertStatus(200)
        self.assertBody('Mrs. B.J. Smegma')

        # Test @expose("alias")
        self.getPage('/expose_dec/call_alias')
        self.assertStatus(200)
        self.assertBody('Mr Nesbitt')
        # Does the original name work?
        self.getPage('/expose_dec/nesbitt')
        self.assertStatus(200)
        self.assertBody('Mr Nesbitt')

        # Test @expose(["alias1", "alias2"])
        self.getPage('/expose_dec/alias1')
        self.assertStatus(200)
        self.assertBody('Mr Ken Andrews')
        self.getPage('/expose_dec/alias2')
        self.assertStatus(200)
        self.assertBody('Mr Ken Andrews')
        # Does the original name work?
        self.getPage('/expose_dec/andrews')
        self.assertStatus(200)
        self.assertBody('Mr Ken Andrews')

        # Test @expose(alias="alias")
        self.getPage('/expose_dec/alias3')
        self.assertStatus(200)
        self.assertBody('Mr. and Mrs. Watson')


class ErrorTests(helper.CPWebCase):

    @staticmethod
    def setup_server():
        def break_header():
            # Add a header after finalize that is invalid
            cherrypy.serving.response.header_list.append((2, 3))
        cherrypy.tools.break_header = cherrypy.Tool(
            'on_end_resource', break_header)

        class Root:

            @cherrypy.expose
            def index(self):
                return 'hello'

            @cherrypy.config(**{'tools.break_header.on': True})
            def start_response_error(self):
                return 'salud!'

            @cherrypy.expose
            def stat(self, path):
                with cherrypy.HTTPError.handle(OSError, 404):
                    os.stat(path)

        root = Root()

        cherrypy.tree.mount(root)

    def test_start_response_error(self):
        self.getPage('/start_response_error')
        self.assertStatus(500)
        self.assertInBody(
            'TypeError: response.header_list key 2 is not a byte string.')

    def test_contextmanager(self):
        self.getPage('/stat/missing')
        self.assertStatus(404)
        body_text = self.body.decode('utf-8')
        assert (
            'No such file or directory' in body_text or
            'cannot find the file specified' in body_text
        )


class TestBinding:
    def test_bind_ephemeral_port(self):
        """
        A server configured to bind to port 0 will bind to an ephemeral
        port and indicate that port number on startup.
        """
        cherrypy.config.reset()
        bind_ephemeral_conf = {
            'server.socket_port': 0,
        }
        cherrypy.config.update(bind_ephemeral_conf)
        cherrypy.engine.start()
        assert cherrypy.server.bound_addr != cherrypy.server.bind_addr
        _host, port = cherrypy.server.bound_addr
        assert port > 0
        cherrypy.engine.stop()
        assert cherrypy.server.bind_addr == cherrypy.server.bound_addr
