"""<MyProject>, a CherryPy application.

Use this as a base for creating new CherryPy applications. When you want
to make a new app, copy and paste this folder to some other location
(maybe site-packages) and rename it to the name of your project,
then tweak as desired.

Even before any tweaking, this should serve a few demonstration pages.
Change to this directory and run:

    cherryd -c site.conf

"""

import cherrypy
from cherrypy import tools, url

import os
local_dir = os.path.join(os.getcwd(), os.path.dirname(__file__))


@cherrypy.config(**{'tools.log_tracebacks.on': True})
class Root:
    """Declaration of the CherryPy app URI structure."""

    @cherrypy.expose
    def index(self):
        """Render HTML-template at the root path of the web-app."""
        return """<html>
<body>Try some <a href='%s?a=7'>other</a> path,
or a <a href='%s?n=14'>default</a> path.<br />
Or, just look at the pretty picture:<br />
<img src='%s' />
</body></html>""" % (url('other'), url('else'),
                     url('files/made_with_cherrypy_small.png'))

    @cherrypy.expose
    def default(self, *args, **kwargs):
        """Render catch-all args and kwargs."""
        return 'args: %s kwargs: %s' % (args, kwargs)

    @cherrypy.expose
    def other(self, a=2, b='bananas', c=None):
        """Render number of fruits based on third argument."""
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        if c is None:
            return 'Have %d %s.' % (int(a), b)
        else:
            return 'Have %d %s, %s.' % (int(a), b, c)

    files = tools.staticdir.handler(
        section='/files',
        dir=os.path.join(local_dir, 'static'),
        # Ignore .php files, etc.
                match=r'\.(css|gif|html?|ico|jpe?g|js|png|swf|xml)$',
    )


root = Root()

# Uncomment the following to use your own favicon instead of CP's default.
# favicon_path = os.path.join(local_dir, "favicon.ico")
# root.favicon_ico = tools.staticfile.handler(filename=favicon_path)
