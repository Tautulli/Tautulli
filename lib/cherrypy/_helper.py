"""Helper functions for CP apps."""

import urllib.parse

from cherrypy._cpcompat import text_or_bytes

import cherrypy


def expose(func=None, alias=None):
    """Expose the function or class.

    Optionally provide an alias or set of aliases.
    """
    def expose_(func):
        func.exposed = True
        if alias is not None:
            if isinstance(alias, text_or_bytes):
                parents[alias.replace('.', '_')] = func
            else:
                for a in alias:
                    parents[a.replace('.', '_')] = func
        return func

    import sys
    import types
    decoratable_types = types.FunctionType, types.MethodType, type,
    if isinstance(func, decoratable_types):
        if alias is None:
            # @expose
            func.exposed = True
            return func
        else:
            # func = expose(func, alias)
            parents = sys._getframe(1).f_locals
            return expose_(func)
    elif func is None:
        if alias is None:
            # @expose()
            parents = sys._getframe(1).f_locals
            return expose_
        else:
            # @expose(alias="alias") or
            # @expose(alias=["alias1", "alias2"])
            parents = sys._getframe(1).f_locals
            return expose_
    else:
        # @expose("alias") or
        # @expose(["alias1", "alias2"])
        parents = sys._getframe(1).f_locals
        alias = func
        return expose_


def popargs(*args, **kwargs):
    """Decorate _cp_dispatch.

    (cherrypy.dispatch.Dispatcher.dispatch_method_name)

    Optional keyword argument: handler=(Object or Function)

    Provides a _cp_dispatch function that pops off path segments into
    cherrypy.request.params under the names specified.  The dispatch
    is then forwarded on to the next vpath element.

    Note that any existing (and exposed) member function of the class that
    popargs is applied to will override that value of the argument.  For
    instance, if you have a method named "list" on the class decorated with
    popargs, then accessing "/list" will call that function instead of popping
    it off as the requested parameter.  This restriction applies to all
    _cp_dispatch functions.  The only way around this restriction is to create
    a "blank class" whose only function is to provide _cp_dispatch.

    If there are path elements after the arguments, or more arguments
    are requested than are available in the vpath, then the 'handler'
    keyword argument specifies the next object to handle the parameterized
    request.  If handler is not specified or is None, then self is used.
    If handler is a function rather than an instance, then that function
    will be called with the args specified and the return value from that
    function used as the next object INSTEAD of adding the parameters to
    cherrypy.request.args.

    This decorator may be used in one of two ways:

    As a class decorator:

    .. code-block:: python

        @cherrypy.popargs('year', 'month', 'day')
        class Blog:
            def index(self, year=None, month=None, day=None):
                #Process the parameters here; any url like
                #/, /2009, /2009/12, or /2009/12/31
                #will fill in the appropriate parameters.

            def create(self):
                #This link will still be available at /create.
                #Defined functions take precedence over arguments.

    Or as a member of a class:

    .. code-block:: python

        class Blog:
            _cp_dispatch = cherrypy.popargs('year', 'month', 'day')
            #...

    The handler argument may be used to mix arguments with built in functions.
    For instance, the following setup allows different activities at the
    day, month, and year level:

    .. code-block:: python

        class DayHandler:
            def index(self, year, month, day):
                #Do something with this day; probably list entries

            def delete(self, year, month, day):
                #Delete all entries for this day

        @cherrypy.popargs('day', handler=DayHandler())
        class MonthHandler:
            def index(self, year, month):
                #Do something with this month; probably list entries

            def delete(self, year, month):
                #Delete all entries for this month

        @cherrypy.popargs('month', handler=MonthHandler())
        class YearHandler:
            def index(self, year):
                #Do something with this year

            #...

        @cherrypy.popargs('year', handler=YearHandler())
        class Root:
            def index(self):
                #...

    """
    # Since keyword arg comes after *args, we have to process it ourselves
    # for lower versions of python.

    handler = None
    handler_call = False
    for k, v in kwargs.items():
        if k == 'handler':
            handler = v
        else:
            tm = "cherrypy.popargs() got an unexpected keyword argument '{0}'"
            raise TypeError(tm.format(k))

    import inspect

    if handler is not None \
            and (hasattr(handler, '__call__') or inspect.isclass(handler)):
        handler_call = True

    def decorated(cls_or_self=None, vpath=None):
        if inspect.isclass(cls_or_self):
            # cherrypy.popargs is a class decorator
            cls = cls_or_self
            name = cherrypy.dispatch.Dispatcher.dispatch_method_name
            setattr(cls, name, decorated)
            return cls

        # We're in the actual function
        self = cls_or_self
        parms = {}
        for arg in args:
            if not vpath:
                break
            parms[arg] = vpath.pop(0)

        if handler is not None:
            if handler_call:
                return handler(**parms)
            else:
                cherrypy.request.params.update(parms)
                return handler

        cherrypy.request.params.update(parms)

        # If we are the ultimate handler, then to prevent our _cp_dispatch
        # from being called again, we will resolve remaining elements through
        # getattr() directly.
        if vpath:
            return getattr(self, vpath.pop(0), None)
        else:
            return self

    return decorated


def url(path='', qs='', script_name=None, base=None, relative=None):
    """Create an absolute URL for the given path.

    If 'path' starts with a slash ('/'), this will return
        (base + script_name + path + qs).
    If it does not start with a slash, this returns
        (base + script_name [+ request.path_info] + path + qs).

    If script_name is None, cherrypy.request will be used
    to find a script_name, if available.

    If base is None, cherrypy.request.base will be used (if available).
    Note that you can use cherrypy.tools.proxy to change this.

    Finally, note that this function can be used to obtain an absolute URL
    for the current request path (minus the querystring) by passing no args.
    If you call url(qs=cherrypy.request.query_string), you should get the
    original browser URL (assuming no internal redirections).

    If relative is None or not provided, request.app.relative_urls will
    be used (if available, else False). If False, the output will be an
    absolute URL (including the scheme, host, vhost, and script_name).
    If True, the output will instead be a URL that is relative to the
    current request path, perhaps including '..' atoms. If relative is
    the string 'server', the output will instead be a URL that is
    relative to the server root; i.e., it will start with a slash.
    """
    if isinstance(qs, (tuple, list, dict)):
        qs = urllib.parse.urlencode(qs)
    if qs:
        qs = '?' + qs

    if cherrypy.request.app:
        if not path.startswith('/'):
            # Append/remove trailing slash from path_info as needed
            # (this is to support mistyped URL's without redirecting;
            # if you want to redirect, use tools.trailing_slash).
            pi = cherrypy.request.path_info
            if cherrypy.request.is_index is True:
                if not pi.endswith('/'):
                    pi = pi + '/'
            elif cherrypy.request.is_index is False:
                if pi.endswith('/') and pi != '/':
                    pi = pi[:-1]

            if path == '':
                path = pi
            else:
                path = urllib.parse.urljoin(pi, path)

        if script_name is None:
            script_name = cherrypy.request.script_name
        if base is None:
            base = cherrypy.request.base

        newurl = base + script_name + normalize_path(path) + qs
    else:
        # No request.app (we're being called outside a request).
        # We'll have to guess the base from server.* attributes.
        # This will produce very different results from the above
        # if you're using vhosts or tools.proxy.
        if base is None:
            base = cherrypy.server.base()

        path = (script_name or '') + path
        newurl = base + normalize_path(path) + qs

    # At this point, we should have a fully-qualified absolute URL.

    if relative is None:
        relative = getattr(cherrypy.request.app, 'relative_urls', False)

    # See http://www.ietf.org/rfc/rfc2396.txt
    if relative == 'server':
        # "A relative reference beginning with a single slash character is
        # termed an absolute-path reference, as defined by <abs_path>..."
        # This is also sometimes called "server-relative".
        newurl = '/' + '/'.join(newurl.split('/', 3)[3:])
    elif relative:
        # "A relative reference that does not begin with a scheme name
        # or a slash character is termed a relative-path reference."
        old = url(relative=False).split('/')[:-1]
        new = newurl.split('/')
        while old and new:
            a, b = old[0], new[0]
            if a != b:
                break
            old.pop(0)
            new.pop(0)
        new = (['..'] * len(old)) + new
        newurl = '/'.join(new)

    return newurl


def normalize_path(path):
    """Resolve given path from relative into absolute form."""
    if './' not in path:
        return path

    # Normalize the URL by removing ./ and ../
    atoms = []
    for atom in path.split('/'):
        if atom == '.':
            pass
        elif atom == '..':
            # Don't pop from empty list
            # (i.e. ignore redundant '..')
            if atoms:
                atoms.pop()
        elif atom:
            atoms.append(atom)

    newpath = '/'.join(atoms)
    # Preserve leading '/'
    if path.startswith('/'):
        newpath = '/' + newpath

    return newpath


####
# Inlined from jaraco.classes 1.4.3
# Ref #1673
class _ClassPropertyDescriptor(object):
    """Descript for read-only class-based property.

    Turns a classmethod-decorated func into a read-only property of that class
    type (means the value cannot be set).
    """

    def __init__(self, fget, fset=None):
        """Initialize a class property descriptor.

        Instantiated by ``_helper.classproperty``.
        """
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        """Return property value."""
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()


def classproperty(func):  # noqa: D401; irrelevant for properties
    """Decorator like classmethod to implement a static class property."""
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return _ClassPropertyDescriptor(func)
####
