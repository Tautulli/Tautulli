# This file is part of CherryPy <http://www.cherrypy.org/>
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:expandtab:fileencoding=utf-8


import cherrypy
from cherrypy.lib import auth_digest
from cherrypy._cpcompat import ntob

from cherrypy.test import helper


def _fetch_users():
    return {'test': 'test', '☃йюзер': 'їпароль'}


get_ha1 = cherrypy.lib.auth_digest.get_ha1_dict_plain(_fetch_users())


class DigestAuthTest(helper.CPWebCase):

    @staticmethod
    def setup_server():
        class Root:

            @cherrypy.expose
            def index(self):
                return 'This is public.'

        class DigestProtected:

            @cherrypy.expose
            def index(self, *args, **kwargs):
                return "Hello %s, you've been authorized." % (
                    cherrypy.request.login)

        conf = {'/digest': {'tools.auth_digest.on': True,
                            'tools.auth_digest.realm': 'localhost',
                            'tools.auth_digest.get_ha1': get_ha1,
                            'tools.auth_digest.key': 'a565c27146791cfb',
                            'tools.auth_digest.debug': True,
                            'tools.auth_digest.accept_charset': 'UTF-8'}}

        root = Root()
        root.digest = DigestProtected()
        cherrypy.tree.mount(root, config=conf)

    def testPublic(self):
        self.getPage('/')
        assert self.status == '200 OK'
        self.assertHeader('Content-Type', 'text/html;charset=utf-8')
        assert self.body == b'This is public.'

    def _test_parametric_digest(self, username, realm):
        test_uri = '/digest/?@/=%2F%40&%f0%9f%99%88=path'

        self.getPage(test_uri)
        assert self.status_code == 401

        msg = 'Digest authentification scheme was not found'
        www_auth_digest = tuple(filter(
            lambda kv: kv[0].lower() == 'www-authenticate'
            and kv[1].startswith('Digest '),
            self.headers,
        ))
        assert len(www_auth_digest) == 1, msg

        items = www_auth_digest[0][-1][7:].split(', ')
        tokens = {}
        for item in items:
            key, value = item.split('=')
            tokens[key.lower()] = value

        assert tokens['realm'] == '"localhost"'
        assert tokens['algorithm'] == '"MD5"'
        assert tokens['qop'] == '"auth"'
        assert tokens['charset'] == '"UTF-8"'

        nonce = tokens['nonce'].strip('"')

        # Test user agent response with a wrong value for 'realm'
        base_auth = ('Digest username="%s", '
                     'realm="%s", '
                     'nonce="%s", '
                     'uri="%s", '
                     'algorithm=MD5, '
                     'response="%s", '
                     'qop=auth, '
                     'nc=%s, '
                     'cnonce="1522e61005789929"')

        encoded_user = username
        encoded_user = encoded_user.encode('utf-8')
        encoded_user = encoded_user.decode('latin1')
        auth_header = base_auth % (
            encoded_user, realm, nonce, test_uri,
            '11111111111111111111111111111111', '00000001',
        )
        auth = auth_digest.HttpDigestAuthorization(auth_header, 'GET')
        # calculate the response digest
        ha1 = get_ha1(auth.realm, auth.username)
        response = auth.request_digest(ha1)
        auth_header = base_auth % (
            encoded_user, realm, nonce, test_uri,
            response, '00000001',
        )
        self.getPage(test_uri, [('Authorization', auth_header)])

    def test_wrong_realm(self):
        # send response with correct response digest, but wrong realm
        self._test_parametric_digest(username='test', realm='wrong realm')
        assert self.status_code == 401

    def test_ascii_user(self):
        self._test_parametric_digest(username='test', realm='localhost')
        assert self.status == '200 OK'
        assert self.body == b"Hello test, you've been authorized."

    def test_unicode_user(self):
        self._test_parametric_digest(username='☃йюзер', realm='localhost')
        assert self.status == '200 OK'
        assert self.body == ntob(
            "Hello ☃йюзер, you've been authorized.", 'utf-8',
        )

    def test_wrong_scheme(self):
        basic_auth = {
            'Authorization': 'Basic foo:bar',
        }
        self.getPage('/digest/', headers=list(basic_auth.items()))
        assert self.status_code == 401
