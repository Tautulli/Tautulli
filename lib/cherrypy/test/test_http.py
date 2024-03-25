# coding: utf-8
"""Tests for managing HTTP issues (malformed requests, etc)."""

import errno
import mimetypes
import socket
import sys
from unittest import mock
import urllib.parse
from http.client import HTTPConnection

import cherrypy
from cherrypy._cpcompat import HTTPSConnection

from cherrypy.test import helper


def is_ascii(text):
    """
    Return True if the text encodes as ascii.
    """
    try:
        text.encode('ascii')
        return True
    except Exception:
        pass
    return False


def encode_filename(filename):
    """
    Given a filename to be used in a multipart/form-data,
    encode the name. Return the key and encoded filename.
    """
    if is_ascii(filename):
        return 'filename', '"{filename}"'.format(**locals())
    encoded = urllib.parse.quote(filename, encoding='utf-8')
    return 'filename*', "'".join((
        'UTF-8',
        '',  # lang
        encoded,
    ))


def encode_multipart_formdata(files):
    """Return (content_type, body) ready for httplib.HTTP instance.

    files: a sequence of (name, filename, value) tuples for multipart uploads.
    filename can be a string or a tuple ('filename string', 'encoding')
    """
    BOUNDARY = '________ThIs_Is_tHe_bouNdaRY_$'
    L = []
    for key, filename, value in files:
        L.append('--' + BOUNDARY)

        fn_key, encoded = encode_filename(filename)
        tmpl = \
            'Content-Disposition: form-data; name="{key}"; {fn_key}={encoded}'
        L.append(tmpl.format(**locals()))
        ct = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        L.append('Content-Type: %s' % ct)
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = '\r\n'.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


class HTTPTests(helper.CPWebCase):

    def make_connection(self):
        if self.scheme == 'https':
            return HTTPSConnection('%s:%s' % (self.interface(), self.PORT))
        else:
            return HTTPConnection('%s:%s' % (self.interface(), self.PORT))

    @staticmethod
    def setup_server():
        class Root:

            @cherrypy.expose
            def index(self, *args, **kwargs):
                return 'Hello world!'

            @cherrypy.expose
            @cherrypy.config(**{'request.process_request_body': False})
            def no_body(self, *args, **kwargs):
                return 'Hello world!'

            @cherrypy.expose
            def post_multipart(self, file):
                """Return a summary ("a * 65536\nb * 65536") of the uploaded
                file.
                """
                contents = file.file.read()
                summary = []
                curchar = None
                count = 0
                for c in contents:
                    if c == curchar:
                        count += 1
                    else:
                        if count:
                            curchar = chr(curchar)
                            summary.append('%s * %d' % (curchar, count))
                        count = 1
                        curchar = c
                if count:
                    curchar = chr(curchar)
                    summary.append('%s * %d' % (curchar, count))
                return ', '.join(summary)

            @cherrypy.expose
            def post_filename(self, myfile):
                '''Return the name of the file which was uploaded.'''
                return myfile.filename

        cherrypy.tree.mount(Root())
        cherrypy.config.update({'server.max_request_body_size': 30000000})

    def test_no_content_length(self):
        # "The presence of a message-body in a request is signaled by the
        # inclusion of a Content-Length or Transfer-Encoding header field in
        # the request's message-headers."
        #
        # Send a message with neither header and no body. Even though
        # the request is of method POST, this should be OK because we set
        # request.process_request_body to False for our handler.
        c = self.make_connection()
        c.request('POST', '/no_body')
        response = c.getresponse()
        self.body = response.fp.read()
        self.status = str(response.status)
        self.assertStatus(200)
        self.assertBody(b'Hello world!')

        # Now send a message that has no Content-Length, but does send a body.
        # Verify that CP times out the socket and responds
        # with 411 Length Required.
        if self.scheme == 'https':
            c = HTTPSConnection('%s:%s' % (self.interface(), self.PORT))
        else:
            c = HTTPConnection('%s:%s' % (self.interface(), self.PORT))

        # `_get_content_length` is needed for Python 3.6+
        with mock.patch.object(
                c,
                '_get_content_length',
                lambda body, method: None,
                create=True):
            # `_set_content_length` is needed for Python 2.7-3.5
            with mock.patch.object(c, '_set_content_length', create=True):
                c.request('POST', '/')

        response = c.getresponse()
        self.body = response.fp.read()
        self.status = str(response.status)
        self.assertStatus(411)

    def test_post_multipart(self):
        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        # generate file contents for a large post
        contents = ''.join([c * 65536 for c in alphabet])

        # encode as multipart form data
        files = [('file', 'file.txt', contents)]
        content_type, body = encode_multipart_formdata(files)
        body = body.encode('Latin-1')

        # post file
        c = self.make_connection()
        c.putrequest('POST', '/post_multipart')
        c.putheader('Content-Type', content_type)
        c.putheader('Content-Length', str(len(body)))
        c.endheaders()
        c.send(body)

        response = c.getresponse()
        self.body = response.fp.read()
        self.status = str(response.status)
        self.assertStatus(200)
        parts = ['%s * 65536' % ch for ch in alphabet]
        self.assertBody(', '.join(parts))

    def test_post_filename_with_special_characters(self):
        """Testing that we can handle filenames with special characters.

        This was reported as a bug in:

        * https://github.com/cherrypy/cherrypy/issues/1146/
        * https://github.com/cherrypy/cherrypy/issues/1397/
        * https://github.com/cherrypy/cherrypy/issues/1694/
        """
        # We'll upload a bunch of files with differing names.
        fnames = [
            'boop.csv', 'foo, bar.csv', 'bar, xxxx.csv', 'file"name.csv',
            'file;name.csv', 'file; name.csv', u'test_łóąä.txt',
        ]
        for fname in fnames:
            files = [('myfile', fname, 'yunyeenyunyue')]
            content_type, body = encode_multipart_formdata(files)
            body = body.encode('Latin-1')

            # post file
            c = self.make_connection()
            c.putrequest('POST', '/post_filename')
            c.putheader('Content-Type', content_type)
            c.putheader('Content-Length', str(len(body)))
            c.endheaders()
            c.send(body)

            response = c.getresponse()
            self.body = response.fp.read()
            self.status = str(response.status)
            self.assertStatus(200)
            self.assertBody(fname)

    def test_malformed_request_line(self):
        if getattr(cherrypy.server, 'using_apache', False):
            return self.skip('skipped due to known Apache differences...')

        # Test missing version in Request-Line
        c = self.make_connection()
        c._output(b'geT /')
        c._send_output()
        if hasattr(c, 'strict'):
            response = c.response_class(c.sock, strict=c.strict, method='GET')
        else:
            # Python 3.2 removed the 'strict' feature, saying:
            # "http.client now always assumes HTTP/1.x compliant servers."
            response = c.response_class(c.sock, method='GET')
        response.begin()
        self.assertEqual(response.status, 400)
        self.assertEqual(response.fp.read(22), b'Malformed Request-Line')
        c.close()

    def test_request_line_split_issue_1220(self):
        params = {
            'intervenant-entreprise-evenement_classaction':
                'evenement-mailremerciements',
            '_path': 'intervenant-entreprise-evenement',
            'intervenant-entreprise-evenement_action-id': 19404,
            'intervenant-entreprise-evenement_id': 19404,
            'intervenant-entreprise_id': 28092,
        }
        Request_URI = '/index?' + urllib.parse.urlencode(params)
        self.assertEqual(len('GET %s HTTP/1.1\r\n' % Request_URI), 256)
        self.getPage(Request_URI)
        self.assertBody('Hello world!')

    def test_malformed_header(self):
        c = self.make_connection()
        c.putrequest('GET', '/')
        c.putheader('Content-Type', 'text/plain')
        # See https://github.com/cherrypy/cherrypy/issues/941
        c._output(b're, 1.2.3.4#015#012')
        c.endheaders()

        response = c.getresponse()
        self.status = str(response.status)
        self.assertStatus(400)
        self.body = response.fp.read(20)
        self.assertBody('Illegal header line.')

    def test_http_over_https(self):
        if self.scheme != 'https':
            return self.skip('skipped (not running HTTPS)... ')

        # Try connecting without SSL.
        conn = HTTPConnection('%s:%s' % (self.interface(), self.PORT))
        conn.putrequest('GET', '/', skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.endheaders()
        response = conn.response_class(conn.sock, method='GET')
        try:
            response.begin()
            self.assertEqual(response.status, 400)
            self.body = response.read()
            self.assertBody('The client sent a plain HTTP request, but this '
                            'server only speaks HTTPS on this port.')
        except socket.error:
            e = sys.exc_info()[1]
            # "Connection reset by peer" is also acceptable.
            if e.errno != errno.ECONNRESET:
                raise

    def test_garbage_in(self):
        # Connect without SSL regardless of server.scheme
        c = HTTPConnection('%s:%s' % (self.interface(), self.PORT))
        c._output(b'gjkgjklsgjklsgjkljklsg')
        c._send_output()
        response = c.response_class(c.sock, method='GET')
        try:
            response.begin()
            self.assertEqual(response.status, 400)
            self.assertEqual(response.fp.read(22),
                             b'Malformed Request-Line')
            c.close()
        except socket.error:
            e = sys.exc_info()[1]
            # "Connection reset by peer" is also acceptable.
            if e.errno != errno.ECONNRESET:
                raise
