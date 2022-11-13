"""
Tutorial - Multiple objects

This tutorial shows you how to create a site structure through multiple
possibly nested request handler objects.
"""

import os.path

import cherrypy


class HomePage:

    @cherrypy.expose
    def index(self):
        return '''
            <p>Hi, this is the home page! Check out the other
            fun stuff on this site:</p>

            <ul>
                <li><a href="/joke/">A silly joke</a></li>
                <li><a href="/links/">Useful links</a></li>
            </ul>'''


class JokePage:

    @cherrypy.expose
    def index(self):
        return '''
            <p>"In Python, how do you create a string of random
            characters?" -- "Read a Perl file!"</p>
            <p>[<a href="../">Return</a>]</p>'''


class LinksPage:

    def __init__(self):
        # Request handler objects can create their own nested request
        # handler objects. Simply create them inside their __init__
        # methods!
        self.extra = ExtraLinksPage()

    @cherrypy.expose
    def index(self):
        # Note the way we link to the extra links page (and back).
        # As you can see, this object doesn't really care about its
        # absolute position in the site tree, since we use relative
        # links exclusively.
        return '''
            <p>Here are some useful links:</p>

            <ul>
                <li>
                    <a href="http://www.cherrypy.dev">The CherryPy Homepage</a>
                </li>
                <li>
                    <a href="http://www.python.org">The Python Homepage</a>
                </li>
            </ul>

            <p>You can check out some extra useful
            links <a href="./extra/">here</a>.</p>

            <p>[<a href="../">Return</a>]</p>
        '''


class ExtraLinksPage:

    @cherrypy.expose
    def index(self):
        # Note the relative link back to the Links page!
        return '''
            <p>Here are some extra useful links:</p>

            <ul>
                <li><a href="http://del.icio.us">del.icio.us</a></li>
                <li><a href="http://www.cherrypy.dev">CherryPy</a></li>
            </ul>

            <p>[<a href="../">Return to links page</a>]</p>'''


# Of course we can also mount request handler objects right here!
root = HomePage()
root.joke = JokePage()
root.links = LinksPage()

# Remember, we don't need to mount ExtraLinksPage here, because
# LinksPage does that itself on initialization. In fact, there is
# no reason why you shouldn't let your root object take care of
# creating all contained request handler objects.


tutconf = os.path.join(os.path.dirname(__file__), 'tutorial.conf')

if __name__ == '__main__':
    # CherryPy always starts with app.root when trying to map request URIs
    # to objects, so we need to mount a request handler root. A request
    # to '/' will be mapped to HelloWorld().index().
    cherrypy.quickstart(root, config=tutconf)
