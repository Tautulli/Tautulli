# -*- coding: utf-8 -*-
import logging
import os
import re
import requests
import time
import zipfile
from datetime import datetime
from getpass import getpass
from threading import Thread, Event
from tqdm import tqdm
from plexapi import compat
from plexapi.exceptions import NotFound

log = logging.getLogger('plexapi')

# Search Types - Plex uses these to filter specific media types when searching.
# Library Types - Populated at runtime
SEARCHTYPES = {'movie': 1, 'show': 2, 'season': 3, 'episode': 4, 'trailer': 5, 'comic': 6, 'person': 7,
               'artist': 8, 'album': 9, 'track': 10, 'picture': 11, 'clip': 12, 'photo': 13, 'photoalbum': 14,
               'playlist': 15, 'playlistFolder': 16, 'collection': 18, 'userPlaylistItem': 1001}
PLEXOBJECTS = {}


class SecretsFilter(logging.Filter):
    """ Logging filter to hide secrets. """

    def __init__(self, secrets=None):
        self.secrets = secrets or set()

    def add_secret(self, secret):
        if secret is not None:
            self.secrets.add(secret)
        return secret

    def filter(self, record):
        cleanargs = list(record.args)
        for i in range(len(cleanargs)):
            if isinstance(cleanargs[i], compat.string_type):
                for secret in self.secrets:
                    cleanargs[i] = cleanargs[i].replace(secret, '<hidden>')
        record.args = tuple(cleanargs)
        return True


def registerPlexObject(cls):
    """ Registry of library types we may come across when parsing XML. This allows us to
        define a few helper functions to dynamically convery the XML into objects. See
        buildItem() below for an example.
    """
    etype = getattr(cls, 'STREAMTYPE', cls.TYPE)
    ehash = '%s.%s' % (cls.TAG, etype) if etype else cls.TAG
    if ehash in PLEXOBJECTS:
        raise Exception('Ambiguous PlexObject definition %s(tag=%s, type=%s) with %s' %
            (cls.__name__, cls.TAG, etype, PLEXOBJECTS[ehash].__name__))
    PLEXOBJECTS[ehash] = cls
    return cls


def cast(func, value):
    """ Cast the specified value to the specified type (returned by func). Currently this
        only support int, float, bool. Should be extended if needed.

        Parameters:
            func (func): Calback function to used cast to type (int, bool, float).
            value (any): value to be cast and returned.
    """
    if value is not None:
        if func == bool:
            return bool(int(value))
        elif func in (int, float):
            try:
                return func(value)
            except ValueError:
                return float('nan')
        return func(value)
    return value


def joinArgs(args):
    """ Returns a query string (uses for HTTP URLs) where only the value is URL encoded.
        Example return value: '?genre=action&type=1337'.

        Parameters:
            args (dict): Arguments to include in query string.
    """
    if not args:
        return ''
    arglist = []
    for key in sorted(args, key=lambda x: x.lower()):
        value = compat.ustr(args[key])
        arglist.append('%s=%s' % (key, compat.quote(value)))
    return '?%s' % '&'.join(arglist)


def lowerFirst(s):
    return s[0].lower() + s[1:]


def rget(obj, attrstr, default=None, delim='.'):  # pragma: no cover
    """ Returns the value at the specified attrstr location within a nexted tree of
        dicts, lists, tuples, functions, classes, etc. The lookup is done recursivley
        for each key in attrstr (split by by the delimiter) This function is heavily
        influenced by the lookups used in Django templates.

        Parameters:
            obj (any): Object to start the lookup in (dict, obj, list, tuple, etc).
            attrstr (str): String to lookup (ex: 'foo.bar.baz.value')
            default (any): Default value to return if not found.
            delim (str): Delimiter separating keys in attrstr.
    """
    try:
        parts = attrstr.split(delim, 1)
        attr = parts[0]
        attrstr = parts[1] if len(parts) == 2 else None
        if isinstance(obj, dict):
            value = obj[attr]
        elif isinstance(obj, list):
            value = obj[int(attr)]
        elif isinstance(obj, tuple):
            value = obj[int(attr)]
        elif isinstance(obj, object):
            value = getattr(obj, attr)
        if attrstr:
            return rget(value, attrstr, default, delim)
        return value
    except:  # noqa: E722
        return default


def searchType(libtype):
    """ Returns the integer value of the library string type.

        Parameters:
            libtype (str): LibType to lookup (movie, show, season, episode, artist, album, track,
                                              collection)
        Raises:
            :class:`plexapi.exceptions.NotFound`: Unknown libtype
    """
    libtype = compat.ustr(libtype)
    if libtype in [compat.ustr(v) for v in SEARCHTYPES.values()]:
        return libtype
    if SEARCHTYPES.get(libtype) is not None:
        return SEARCHTYPES[libtype]
    raise NotFound('Unknown libtype: %s' % libtype)


def threaded(callback, listargs):
    """ Returns the result of <callback> for each set of \*args in listargs. Each call
        to <callback> is called concurrently in their own separate threads.

        Parameters:
            callback (func): Callback function to apply to each set of \*args.
            listargs (list): List of lists; \*args to pass each thread.
    """
    threads, results = [], []
    job_is_done_event = Event()
    for args in listargs:
        args += [results, len(results)]
        results.append(None)
        threads.append(Thread(target=callback, args=args, kwargs=dict(job_is_done_event=job_is_done_event)))
        threads[-1].setDaemon(True)
        threads[-1].start()
    while not job_is_done_event.is_set():
        if all([not t.is_alive() for t in threads]):
            break
        time.sleep(0.05)

    return [r for r in results if r is not None]


def toDatetime(value, format=None):
    """ Returns a datetime object from the specified value.

        Parameters:
            value (str): value to return as a datetime
            format (str): Format to pass strftime (optional; if value is a str).
    """
    if value and value is not None:
        if format:
            try:
                value = datetime.strptime(value, format)
            except ValueError:
                log.info('Failed to parse %s to datetime, defaulting to None', value)
                return None
        else:
            # https://bugs.python.org/issue30684
            # And platform support for before epoch seems to be flaky.
            # TODO check for others errors too.
            if int(value) <= 0:
                value = 86400
            value = datetime.fromtimestamp(int(value))
    return value


def toList(value, itemcast=None, delim=','):
    """ Returns a list of strings from the specified value.

        Parameters:
            value (str): comma delimited string to convert to list.
            itemcast (func): Function to cast each list item to (default str).
            delim (str): string delimiter (optional; default ',').
    """
    value = value or ''
    itemcast = itemcast or str
    return [itemcast(item) for item in value.split(delim) if item != '']


def downloadSessionImages(server, filename=None, height=150, width=150,
                          opacity=100, saturation=100):  # pragma: no cover
    """ Helper to download a bif image or thumb.url from plex.server.sessions.

       Parameters:
           filename (str): default to None,
           height (int): Height of the image.
           width (int): width of the image.
           opacity (int): Opacity of the resulting image (possibly deprecated).
           saturation (int): Saturating of the resulting image.

       Returns:
            {'hellowlol': {'filepath': '<filepath>', 'url': 'http://<url>'},
            {'<username>': {filepath, url}}, ...
    """
    info = {}
    for media in server.sessions():
        url = None
        for part in media.iterParts():
            if media.thumb:
                url = media.thumb
            if part.indexes:  # always use bif images if available.
                url = '/library/parts/%s/indexes/%s/%s' % (part.id, part.indexes.lower(), media.viewOffset)
        if url:
            if filename is None:
                prettyname = media._prettyfilename()
                filename = 'session_transcode_%s_%s_%s' % (media.usernames[0], prettyname, int(time.time()))
            url = server.transcodeImage(url, height, width, opacity, saturation)
            filepath = download(url, filename=filename)
            info['username'] = {'filepath': filepath, 'url': url}
    return info


def download(url, token, filename=None, savepath=None, session=None, chunksize=4024,
             unpack=False, mocked=False, showstatus=False):
    """ Helper to download a thumb, videofile or other media item. Returns the local
        path to the downloaded file.

       Parameters:
            url (str): URL where the content be reached.
            token (str): Plex auth token to include in headers.
            filename (str): Filename of the downloaded file, default None.
            savepath (str): Defaults to current working dir.
            chunksize (int): What chunksize read/write at the time.
            mocked (bool): Helper to do evertything except write the file.
            unpack (bool): Unpack the zip file.
            showstatus(bool): Display a progressbar.

        Example:
            >>> download(a_episode.getStreamURL(), a_episode.location)
            /path/to/file
    """
    # fetch the data to be saved
    session = session or requests.Session()
    headers = {'X-Plex-Token': token}
    response = session.get(url, headers=headers, stream=True)
    # make sure the savepath directory exists
    savepath = savepath or os.getcwd()
    compat.makedirs(savepath, exist_ok=True)

    # try getting filename from header if not specified in arguments (used for logs, db)
    if not filename and response.headers.get('Content-Disposition'):
        filename = re.findall(r'filename=\"(.+)\"', response.headers.get('Content-Disposition'))
        filename = filename[0] if filename[0] else None

    filename = os.path.basename(filename)
    fullpath = os.path.join(savepath, filename)
    # append file.ext from content-type if not already there
    extension = os.path.splitext(fullpath)[-1]
    if not extension:
        contenttype = response.headers.get('content-type')
        if contenttype and 'image' in contenttype:
            fullpath += contenttype.split('/')[1]

    # check this is a mocked download (testing)
    if mocked:
        log.debug('Mocked download %s', fullpath)
        return fullpath

    # save the file to disk
    log.info('Downloading: %s', fullpath)
    if showstatus:  # pragma: no cover
        total = int(response.headers.get('content-length', 0))
        bar = tqdm(unit='B', unit_scale=True, total=total, desc=filename)

    with open(fullpath, 'wb') as handle:
        for chunk in response.iter_content(chunk_size=chunksize):
            handle.write(chunk)
            if showstatus:
                bar.update(len(chunk))

    if showstatus:  # pragma: no cover
        bar.close()
    # check we want to unzip the contents
    if fullpath.endswith('zip') and unpack:
        with zipfile.ZipFile(fullpath, 'r') as handle:
            handle.extractall(savepath)

    return fullpath


def tag_helper(tag, items, locked=True, remove=False):
    """ Simple tag helper for editing a object. """
    if not isinstance(items, list):
        items = [items]
    data = {}
    if not remove:
        for i, item in enumerate(items):
            tagname = '%s[%s].tag.tag' % (tag, i)
            data[tagname] = item
    if remove:
        tagname = '%s[].tag.tag-' % tag
        data[tagname] = ','.join(items)
    data['%s.locked' % tag] = 1 if locked else 0
    return data


def getMyPlexAccount(opts=None):  # pragma: no cover
    """ Helper function tries to get a MyPlex Account instance by checking
        the the following locations for a username and password. This is
        useful to create user-friendly command line tools.
        1. command-line options (opts).
        2. environment variables and config.ini
        3. Prompt on the command line.
    """
    from plexapi import CONFIG
    from plexapi.myplex import MyPlexAccount
    # 1. Check command-line options
    if opts and opts.username and opts.password:
        print('Authenticating with Plex.tv as %s..' % opts.username)
        return MyPlexAccount(opts.username, opts.password)
    # 2. Check Plexconfig (environment variables and config.ini)
    config_username = CONFIG.get('auth.myplex_username')
    config_password = CONFIG.get('auth.myplex_password')
    if config_username and config_password:
        print('Authenticating with Plex.tv as %s..' % config_username)
        return MyPlexAccount(config_username, config_password)
    # 3. Prompt for username and password on the command line
    username = input('What is your plex.tv username: ')
    password = getpass('What is your plex.tv password: ')
    print('Authenticating with Plex.tv as %s..' % username)
    return MyPlexAccount(username, password)


def choose(msg, items, attr):  # pragma: no cover
    """ Command line helper to display a list of choices, asking the
        user to choose one of the options.
    """
    # Return the first item if there is only one choice
    if len(items) == 1:
        return items[0]
    # Print all choices to the command line
    print()
    for index, i in enumerate(items):
        name = attr(i) if callable(attr) else getattr(i, attr)
        print('  %s: %s' % (index, name))
    print()
    # Request choice from the user
    while True:
        try:
            inp = input('%s: ' % msg)
            if any(s in inp for s in (':', '::', '-')):
                idx = slice(*map(lambda x: int(x.strip()) if x.strip() else None, inp.split(':')))
                return items[idx]
            else:
                return items[int(inp)]

        except (ValueError, IndexError):
            pass
