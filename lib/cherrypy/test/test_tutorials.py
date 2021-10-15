import sys
import importlib

import cherrypy
from cherrypy.test import helper


class TutorialTest(helper.CPWebCase):

    @classmethod
    def setup_server(cls):
        """
        Mount something so the engine starts.
        """
        class Dummy:
            pass
        cherrypy.tree.mount(Dummy())

    @staticmethod
    def load_module(name):
        """
        Import or reload tutorial module as needed.
        """
        target = 'cherrypy.tutorial.' + name
        if target in sys.modules:
            module = importlib.reload(sys.modules[target])
        else:
            module = importlib.import_module(target)
        return module

    @classmethod
    def setup_tutorial(cls, name, root_name, config={}):
        cherrypy.config.reset()
        module = cls.load_module(name)
        root = getattr(module, root_name)
        conf = getattr(module, 'tutconf')
        class_types = type,
        if isinstance(root, class_types):
            root = root()
        cherrypy.tree.mount(root, config=conf)
        cherrypy.config.update(config)

    def test01HelloWorld(self):
        self.setup_tutorial('tut01_helloworld', 'HelloWorld')
        self.getPage('/')
        self.assertBody('Hello world!')

    def test02ExposeMethods(self):
        self.setup_tutorial('tut02_expose_methods', 'HelloWorld')
        self.getPage('/show_msg')
        self.assertBody('Hello world!')

    def test03GetAndPost(self):
        self.setup_tutorial('tut03_get_and_post', 'WelcomePage')

        # Try different GET queries
        self.getPage('/greetUser?name=Bob')
        self.assertBody("Hey Bob, what's up?")

        self.getPage('/greetUser')
        self.assertBody('Please enter your name <a href="./">here</a>.')

        self.getPage('/greetUser?name=')
        self.assertBody('No, really, enter your name <a href="./">here</a>.')

        # Try the same with POST
        self.getPage('/greetUser', method='POST', body='name=Bob')
        self.assertBody("Hey Bob, what's up?")

        self.getPage('/greetUser', method='POST', body='name=')
        self.assertBody('No, really, enter your name <a href="./">here</a>.')

    def test04ComplexSite(self):
        self.setup_tutorial('tut04_complex_site', 'root')

        msg = '''
            <p>Here are some extra useful links:</p>

            <ul>
                <li><a href="http://del.icio.us">del.icio.us</a></li>
                <li><a href="http://www.cherrypy.org">CherryPy</a></li>
            </ul>

            <p>[<a href="../">Return to links page</a>]</p>'''
        self.getPage('/links/extra/')
        self.assertBody(msg)

    def test05DerivedObjects(self):
        self.setup_tutorial('tut05_derived_objects', 'HomePage')
        msg = '''
            <html>
            <head>
                <title>Another Page</title>
            <head>
            <body>
            <h2>Another Page</h2>

            <p>
            And this is the amazing second page!
            </p>

            </body>
            </html>
        '''
        # the tutorial has some annoying spaces in otherwise blank lines
        msg = msg.replace('</h2>\n\n', '</h2>\n        \n')
        msg = msg.replace('</p>\n\n', '</p>\n        \n')
        self.getPage('/another/')
        self.assertBody(msg)

    def test06DefaultMethod(self):
        self.setup_tutorial('tut06_default_method', 'UsersPage')
        self.getPage('/hendrik')
        self.assertBody('Hendrik Mans, CherryPy co-developer & crazy German '
                        '(<a href="./">back</a>)')

    def test07Sessions(self):
        self.setup_tutorial('tut07_sessions', 'HitCounter')

        self.getPage('/')
        self.assertBody(
            "\n            During your current session, you've viewed this"
            '\n            page 1 times! Your life is a patio of fun!'
            '\n        ')

        self.getPage('/', self.cookies)
        self.assertBody(
            "\n            During your current session, you've viewed this"
            '\n            page 2 times! Your life is a patio of fun!'
            '\n        ')

    def test08GeneratorsAndYield(self):
        self.setup_tutorial('tut08_generators_and_yield', 'GeneratorDemo')
        self.getPage('/')
        self.assertBody('<html><body><h2>Generators rule!</h2>'
                        '<h3>List of users:</h3>'
                        'Remi<br/>Carlos<br/>Hendrik<br/>Lorenzo Lamas<br/>'
                        '</body></html>')

    def test09Files(self):
        self.setup_tutorial('tut09_files', 'FileDemo')

        # Test upload
        filesize = 5
        h = [('Content-type', 'multipart/form-data; boundary=x'),
             ('Content-Length', str(105 + filesize))]
        b = ('--x\n'
             'Content-Disposition: form-data; name="myFile"; '
             'filename="hello.txt"\r\n'
             'Content-Type: text/plain\r\n'
             '\r\n')
        b += 'a' * filesize + '\n' + '--x--\n'
        self.getPage('/upload', h, 'POST', b)
        self.assertBody('''<html>
        <body>
            myFile length: %d<br />
            myFile filename: hello.txt<br />
            myFile mime-type: text/plain
        </body>
        </html>''' % filesize)

        # Test download
        self.getPage('/download')
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'application/x-download')
        self.assertHeader('Content-Disposition',
                          # Make sure the filename is quoted.
                          'attachment; filename="pdf_file.pdf"')
        self.assertEqual(len(self.body), 85698)

    def test10HTTPErrors(self):
        self.setup_tutorial('tut10_http_errors', 'HTTPErrorDemo')

        @cherrypy.expose
        def traceback_setting():
            return repr(cherrypy.request.show_tracebacks)
        cherrypy.tree.mount(traceback_setting, '/traceback_setting')

        self.getPage('/')
        self.assertInBody("""<a href="toggleTracebacks">""")
        self.assertInBody("""<a href="/doesNotExist">""")
        self.assertInBody("""<a href="/error?code=403">""")
        self.assertInBody("""<a href="/error?code=500">""")
        self.assertInBody("""<a href="/messageArg">""")

        self.getPage('/traceback_setting')
        setting = self.body
        self.getPage('/toggleTracebacks')
        self.assertStatus((302, 303))
        self.getPage('/traceback_setting')
        self.assertBody(str(not eval(setting)))

        self.getPage('/error?code=500')
        self.assertStatus(500)
        self.assertInBody('The server encountered an unexpected condition '
                          'which prevented it from fulfilling the request.')

        self.getPage('/error?code=403')
        self.assertStatus(403)
        self.assertInBody("<h2>You can't do that!</h2>")

        self.getPage('/messageArg')
        self.assertStatus(500)
        self.assertInBody("If you construct an HTTPError with a 'message'")
