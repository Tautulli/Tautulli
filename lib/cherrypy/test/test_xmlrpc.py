import sys
import socket

from xmlrpc.client import (
    DateTime, Fault,
    ServerProxy, SafeTransport
)

import cherrypy
from cherrypy import _cptools
from cherrypy.test import helper

HTTPSTransport = SafeTransport

# Python 3.0's SafeTransport still mistakenly checks for socket.ssl
if not hasattr(socket, 'ssl'):
    socket.ssl = True


def setup_server():

    class Root:

        @cherrypy.expose
        def index(self):
            return "I'm a standard index!"

    class XmlRpc(_cptools.XMLRPCController):

        @cherrypy.expose
        def foo(self):
            return 'Hello world!'

        @cherrypy.expose
        def return_single_item_list(self):
            return [42]

        @cherrypy.expose
        def return_string(self):
            return 'here is a string'

        @cherrypy.expose
        def return_tuple(self):
            return ('here', 'is', 1, 'tuple')

        @cherrypy.expose
        def return_dict(self):
            return dict(a=1, b=2, c=3)

        @cherrypy.expose
        def return_composite(self):
            return dict(a=1, z=26), 'hi', ['welcome', 'friend']

        @cherrypy.expose
        def return_int(self):
            return 42

        @cherrypy.expose
        def return_float(self):
            return 3.14

        @cherrypy.expose
        def return_datetime(self):
            return DateTime((2003, 10, 7, 8, 1, 0, 1, 280, -1))

        @cherrypy.expose
        def return_boolean(self):
            return True

        @cherrypy.expose
        def test_argument_passing(self, num):
            return num * 2

        @cherrypy.expose
        def test_returning_Fault(self):
            return Fault(1, 'custom Fault response')

    root = Root()
    root.xmlrpc = XmlRpc()
    cherrypy.tree.mount(root, config={'/': {
        'request.dispatch': cherrypy.dispatch.XMLRPCDispatcher(),
        'tools.xmlrpc.allow_none': 0,
    }})


class XmlRpcTest(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def testXmlRpc(self):

        scheme = self.scheme
        if scheme == 'https':
            url = 'https://%s:%s/xmlrpc/' % (self.interface(), self.PORT)
            proxy = ServerProxy(url, transport=HTTPSTransport())
        else:
            url = 'http://%s:%s/xmlrpc/' % (self.interface(), self.PORT)
            proxy = ServerProxy(url)

        # begin the tests ...
        self.getPage('/xmlrpc/foo')
        self.assertBody('Hello world!')

        self.assertEqual(proxy.return_single_item_list(), [42])
        self.assertNotEqual(proxy.return_single_item_list(), 'one bazillion')
        self.assertEqual(proxy.return_string(), 'here is a string')
        self.assertEqual(proxy.return_tuple(),
                         list(('here', 'is', 1, 'tuple')))
        self.assertEqual(proxy.return_dict(), {'a': 1, 'c': 3, 'b': 2})
        self.assertEqual(proxy.return_composite(),
                         [{'a': 1, 'z': 26}, 'hi', ['welcome', 'friend']])
        self.assertEqual(proxy.return_int(), 42)
        self.assertEqual(proxy.return_float(), 3.14)
        self.assertEqual(proxy.return_datetime(),
                         DateTime((2003, 10, 7, 8, 1, 0, 1, 280, -1)))
        self.assertEqual(proxy.return_boolean(), True)
        self.assertEqual(proxy.test_argument_passing(22), 22 * 2)

        # Test an error in the page handler (should raise an xmlrpclib.Fault)
        try:
            proxy.test_argument_passing({})
        except Exception:
            x = sys.exc_info()[1]
            self.assertEqual(x.__class__, Fault)
            self.assertEqual(x.faultString, ('unsupported operand type(s) '
                                             "for *: 'dict' and 'int'"))
        else:
            self.fail('Expected xmlrpclib.Fault')

        # https://github.com/cherrypy/cherrypy/issues/533
        # if a method is not found, an xmlrpclib.Fault should be raised
        try:
            proxy.non_method()
        except Exception:
            x = sys.exc_info()[1]
            self.assertEqual(x.__class__, Fault)
            self.assertEqual(x.faultString,
                             'method "non_method" is not supported')
        else:
            self.fail('Expected xmlrpclib.Fault')

        # Test returning a Fault from the page handler.
        try:
            proxy.test_returning_Fault()
        except Exception:
            x = sys.exc_info()[1]
            self.assertEqual(x.__class__, Fault)
            self.assertEqual(x.faultString, ('custom Fault response'))
        else:
            self.fail('Expected xmlrpclib.Fault')
