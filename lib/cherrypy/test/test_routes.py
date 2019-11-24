"""Test Routes dispatcher."""
import os
import importlib

import pytest

import cherrypy
from cherrypy.test import helper

curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))


class RoutesDispatchTest(helper.CPWebCase):
    """Routes dispatcher test suite."""

    @staticmethod
    def setup_server():
        """Set up cherrypy test instance."""
        try:
            importlib.import_module('routes')
        except ImportError:
            pytest.skip('Install routes to test RoutesDispatcher code')

        class Dummy:

            def index(self):
                return 'I said good day!'

        class City:

            def __init__(self, name):
                self.name = name
                self.population = 10000

            @cherrypy.config(**{
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [
                    ('Content-Language', 'en-GB'),
                ],
            })
            def index(self, **kwargs):
                return 'Welcome to %s, pop. %s' % (self.name, self.population)

            def update(self, **kwargs):
                self.population = kwargs['pop']
                return 'OK'

        d = cherrypy.dispatch.RoutesDispatcher()
        d.connect(action='index', name='hounslow', route='/hounslow',
                  controller=City('Hounslow'))
        d.connect(
            name='surbiton', route='/surbiton', controller=City('Surbiton'),
            action='index', conditions=dict(method=['GET']))
        d.mapper.connect('/surbiton', controller='surbiton',
                         action='update', conditions=dict(method=['POST']))
        d.connect('main', ':action', controller=Dummy())

        conf = {'/': {'request.dispatch': d}}
        cherrypy.tree.mount(root=None, config=conf)

    def test_Routes_Dispatch(self):
        """Check that routes package based URI dispatching works correctly."""
        self.getPage('/hounslow')
        self.assertStatus('200 OK')
        self.assertBody('Welcome to Hounslow, pop. 10000')

        self.getPage('/foo')
        self.assertStatus('404 Not Found')

        self.getPage('/surbiton')
        self.assertStatus('200 OK')
        self.assertBody('Welcome to Surbiton, pop. 10000')

        self.getPage('/surbiton', method='POST', body='pop=1327')
        self.assertStatus('200 OK')
        self.assertBody('OK')
        self.getPage('/surbiton')
        self.assertStatus('200 OK')
        self.assertHeader('Content-Language', 'en-GB')
        self.assertBody('Welcome to Surbiton, pop. 1327')
