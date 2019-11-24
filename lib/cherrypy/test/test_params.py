import sys
import textwrap

import cherrypy
from cherrypy.test import helper


class ParamsTest(helper.CPWebCase):
    @staticmethod
    def setup_server():
        class Root:
            @cherrypy.expose
            @cherrypy.tools.json_out()
            @cherrypy.tools.params()
            def resource(self, limit=None, sort=None):
                return type(limit).__name__
            # for testing on Py 2
            resource.__annotations__ = {'limit': int}
        conf = {'/': {'tools.params.on': True}}
        cherrypy.tree.mount(Root(), config=conf)

    def test_pass(self):
        self.getPage('/resource')
        self.assertStatus(200)
        self.assertBody('"NoneType"')

        self.getPage('/resource?limit=0')
        self.assertStatus(200)
        self.assertBody('"int"')

    def test_error(self):
        self.getPage('/resource?limit=')
        self.assertStatus(400)
        self.assertInBody('invalid literal for int')

        cherrypy.config['tools.params.error'] = 422
        self.getPage('/resource?limit=')
        self.assertStatus(422)
        self.assertInBody('invalid literal for int')

        cherrypy.config['tools.params.exception'] = TypeError
        self.getPage('/resource?limit=')
        self.assertStatus(500)

    def test_syntax(self):
        if sys.version_info < (3,):
            return self.skip('skipped (Python 3 only)')
        code = textwrap.dedent("""
            class Root:
                @cherrypy.expose
                @cherrypy.tools.params()
                def resource(self, limit: int):
                    return type(limit).__name__
            conf = {'/': {'tools.params.on': True}}
            cherrypy.tree.mount(Root(), config=conf)
            """)
        exec(code)

        self.getPage('/resource?limit=0')
        self.assertStatus(200)
        self.assertBody('int')
