# -*- coding: utf-8 -*-
import base64
import functools
import json
import logging
import os
import re
import string
import time
import unicodedata
import warnings
import zipfile
from collections import deque
from datetime import datetime, timedelta
from getpass import getpass
from hashlib import sha1
from threading import Event, Thread
from urllib.parse import quote

import requests
from requests.status_codes import _codes as codes

from plexapi.exceptions import BadRequest, NotFound, Unauthorized

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

log = logging.getLogger('plexapi')

# Search Types - Plex uses these to filter specific media types when searching.
SEARCHTYPES = {
    'movie': 1,
    'show': 2,
    'season': 3,
    'episode': 4,
    'trailer': 5,
    'comic': 6,
    'person': 7,
    'artist': 8,
    'album': 9,
    'track': 10,
    'picture': 11,
    'clip': 12,
    'photo': 13,
    'photoalbum': 14,
    'playlist': 15,
    'playlistFolder': 16,
    'collection': 18,
    'optimizedVersion': 42,
    'userPlaylistItem': 1001,
}
REVERSESEARCHTYPES = {v: k for k, v in SEARCHTYPES.items()}

# Tag Types - Plex uses these to filter specific tags when searching.
TAGTYPES = {
    'tag': 0,
    'genre': 1,
    'collection': 2,
    'director': 4,
    'writer': 5,
    'role': 6,
    'producer': 7,
    'country': 8,
    'chapter': 9,
    'review': 10,
    'label': 11,
    'marker': 12,
    'mediaProcessingTarget': 42,
    'make': 200,
    'model': 201,
    'aperture': 202,
    'exposure': 203,
    'iso': 204,
    'lens': 205,
    'device': 206,
    'autotag': 207,
    'mood': 300,
    'style': 301,
    'format': 302,
    'similar': 305,
    'concert': 306,
    'banner': 311,
    'poster': 312,
    'art': 313,
    'guid': 314,
    'ratingImage': 316,
    'theme': 317,
    'studio': 318,
    'network': 319,
    'place': 400,
}
REVERSETAGTYPES = {v: k for k, v in TAGTYPES.items()}

# Plex Objects - Populated at runtime
PLEXOBJECTS = {}


class SecretsFilter(logging.Filter):
    """ Logging filter to hide secrets. """

    def __init__(self, secrets=None):
        self.secrets = secrets or set()

    def add_secret(self, secret):
        if secret is not None and secret != '':
            self.secrets.add(secret)
        return secret

    def filter(self, record):
        cleanargs = list(record.args)
        for i in range(len(cleanargs)):
            if isinstance(cleanargs[i], str):
                for secret in self.secrets:
                    cleanargs[i] = cleanargs[i].replace(secret, '<hidden>')
        record.args = tuple(cleanargs)
        return True


def registerPlexObject(cls):
    """ Registry of library types we may come across when parsing XML. This allows us to
        define a few helper functions to dynamically convert the XML into objects. See
        buildItem() below for an example.
    """
    etype = getattr(cls, 'STREAMTYPE', getattr(cls, 'TAGTYPE', cls.TYPE))
    ehash = f'{cls.TAG}.{etype}' if etype else cls.TAG
    if getattr(cls, '_SESSIONTYPE', None):
        ehash = f"{ehash}.session"
    elif getattr(cls, '_HISTORYTYPE', None):
        ehash = f"{ehash}.history"
    if ehash in PLEXOBJECTS:
        raise Exception(f'Ambiguous PlexObject definition {cls.__name__}(tag={cls.TAG}, type={etype}) '
                        f'with {PLEXOBJECTS[ehash].__name__}')
    PLEXOBJECTS[ehash] = cls
    return cls


def cast(func, value):
    """ Cast the specified value to the specified type (returned by func). Currently this
        only support str, int, float, bool. Should be extended if needed.

        Parameters:
            func (func): Callback function to used cast to type (int, bool, float).
            value (any): value to be cast and returned.
    """
    if value is not None:
        if func == bool:
            if value in (1, True, "1", "true"):
                return True
            elif value in (0, False, "0", "false"):
                return False
            else:
                raise ValueError(value)

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
        value = str(args[key])
        arglist.append(f"{key}={quote(value, safe='')}")
    return f"?{'&'.join(arglist)}"


def lowerFirst(s):
    return s[0].lower() + s[1:]


def rget(obj, attrstr, default=None, delim='.'):  # pragma: no cover
    """ Returns the value at the specified attrstr location within a nested tree of
        dicts, lists, tuples, functions, classes, etc. The lookup is done recursively
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
            libtype (str): LibType to lookup (See :data:`~plexapi.utils.SEARCHTYPES`)

        Raises:
            :exc:`~plexapi.exceptions.NotFound`: Unknown libtype
    """
    libtype = str(libtype)
    try:
        return SEARCHTYPES[libtype]
    except KeyError:
        if libtype in [str(k) for k in REVERSESEARCHTYPES]:
            return libtype
        raise NotFound(f'Unknown libtype: {libtype}') from None


def reverseSearchType(libtype):
    """ Returns the string value of the library type.

        Parameters:
            libtype (int): Integer value of the library type.

        Raises:
            :exc:`~plexapi.exceptions.NotFound`: Unknown libtype
    """
    try:
        return REVERSESEARCHTYPES[int(libtype)]
    except (KeyError, ValueError):
        if libtype in SEARCHTYPES:
            return libtype
        raise NotFound(f'Unknown libtype: {libtype}') from None


def tagType(tag):
    """ Returns the integer value of the library tag type.

        Parameters:
            tag (str): Tag to lookup (See :data:`~plexapi.utils.TAGTYPES`)

        Raises:
            :exc:`~plexapi.exceptions.NotFound`: Unknown tag
    """
    tag = str(tag)
    try:
        return TAGTYPES[tag]
    except KeyError:
        if tag in [str(k) for k in REVERSETAGTYPES]:
            return tag
        raise NotFound(f'Unknown tag: {tag}') from None


def reverseTagType(tag):
    """ Returns the string value of the library tag type.

        Parameters:
            tag (int): Integer value of the library tag type.

        Raises:
            :exc:`~plexapi.exceptions.NotFound`: Unknown tag
    """
    try:
        return REVERSETAGTYPES[int(tag)]
    except (KeyError, ValueError):
        if tag in TAGTYPES:
            return tag
        raise NotFound(f'Unknown tag: {tag}') from None


def threaded(callback, listargs):
    """ Returns the result of <callback> for each set of `*args` in listargs. Each call
        to <callback> is called concurrently in their own separate threads.

        Parameters:
            callback (func): Callback function to apply to each set of `*args`.
            listargs (list): List of lists; `*args` to pass each thread.
    """
    threads, results = [], []
    job_is_done_event = Event()
    for args in listargs:
        args += [results, len(results)]
        results.append(None)
        threads.append(Thread(target=callback, args=args, kwargs=dict(job_is_done_event=job_is_done_event)))
        threads[-1].daemon = True
        threads[-1].start()
    while not job_is_done_event.is_set():
        if all(not t.is_alive() for t in threads):
            break
        time.sleep(0.05)

    return [r for r in results if r is not None]


def toDatetime(value, format=None):
    """ Returns a datetime object from the specified value.

        Parameters:
            value (str): value to return as a datetime
            format (str): Format to pass strftime (optional; if value is a str).
    """
    if value is not None:
        if format:
            try:
                return datetime.strptime(value, format)
            except ValueError:
                log.info('Failed to parse "%s" to datetime as format "%s", defaulting to None', value, format)
                return None
        else:
            try:
                value = int(value)
            except ValueError:
                log.info('Failed to parse "%s" to datetime as timestamp, defaulting to None', value)
                return None
            try:
                return datetime.fromtimestamp(value)
            except (OSError, OverflowError):
                try:
                    return datetime.fromtimestamp(0) + timedelta(seconds=value)
                except OverflowError:
                    log.info('Failed to parse "%s" to datetime as timestamp (out-of-bounds), defaulting to None', value)
                    return None
    return value


def millisecondToHumanstr(milliseconds):
    """ Returns human readable time duration [D day[s], ]HH:MM:SS.UUU from milliseconds.

        Parameters:
            milliseconds (str, int): time duration in milliseconds.
    """
    milliseconds = int(milliseconds)
    if milliseconds < 0:
        return '-' + millisecondToHumanstr(abs(milliseconds))
    secs, ms = divmod(milliseconds, 1000)
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)
    return ('' if days == 0 else f'{days} day{"s" if days > 1 else ""}, ') + f'{hours:02d}:{mins:02d}:{secs:02d}.{ms:03d}'


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


def cleanFilename(filename, replace='_'):
    whitelist = f"-_.()[] {string.ascii_letters}{string.digits}"
    cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
    cleaned_filename = ''.join(c if c in whitelist else replace for c in cleaned_filename)
    return cleaned_filename


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
                url = f'/library/parts/{part.id}/indexes/{part.indexes.lower()}/{media.viewOffset}'
        if url:
            if filename is None:
                prettyname = media._prettyfilename()
                filename = f'session_transcode_{media.usernames[0]}_{prettyname}_{int(time.time())}'
            url = server.transcodeImage(url, height, width, opacity, saturation)
            filepath = download(url, server._token, filename=filename)
            info['username'] = {'filepath': filepath, 'url': url}
    return info


def download(url, token, filename=None, savepath=None, session=None, chunksize=4024,   # noqa: C901
             unpack=False, mocked=False, showstatus=False):
    """ Helper to download a thumb, videofile or other media item. Returns the local
        path to the downloaded file.

       Parameters:
            url (str): URL where the content be reached.
            token (str): Plex auth token to include in headers.
            filename (str): Filename of the downloaded file, default None.
            savepath (str): Defaults to current working dir.
            chunksize (int): What chunksize read/write at the time.
            mocked (bool): Helper to do everything except write the file.
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
    if response.status_code not in (200, 201, 204):
        codename = codes.get(response.status_code)[0]
        errtext = response.text.replace('\n', ' ')
        message = f'({response.status_code}) {codename}; {response.url} {errtext}'
        if response.status_code == 401:
            raise Unauthorized(message)
        elif response.status_code == 404:
            raise NotFound(message)
        else:
            raise BadRequest(message)

    # make sure the savepath directory exists
    savepath = savepath or os.getcwd()
    os.makedirs(savepath, exist_ok=True)

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
    if showstatus and tqdm:  # pragma: no cover
        total = int(response.headers.get('content-length', 0))
        bar = tqdm(unit='B', unit_scale=True, total=total, desc=filename)

    with open(fullpath, 'wb') as handle:
        for chunk in response.iter_content(chunk_size=chunksize):
            handle.write(chunk)
            if showstatus and tqdm:
                bar.update(len(chunk))

    if showstatus and tqdm:  # pragma: no cover
        bar.close()
    # check we want to unzip the contents
    if fullpath.endswith('zip') and unpack:
        with zipfile.ZipFile(fullpath, 'r') as handle:
            handle.extractall(savepath)

    return fullpath


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
        print(f'Authenticating with Plex.tv as {opts.username}..')
        return MyPlexAccount(opts.username, opts.password)
    # 2. Check Plexconfig (environment variables and config.ini)
    config_username = CONFIG.get('auth.myplex_username')
    config_password = CONFIG.get('auth.myplex_password')
    if config_username and config_password:
        print(f'Authenticating with Plex.tv as {config_username}..')
        return MyPlexAccount(config_username, config_password)
    config_token = CONFIG.get('auth.server_token')
    if config_token:
        print('Authenticating with Plex.tv with token')
        return MyPlexAccount(token=config_token)
    # 3. Prompt for username and password on the command line
    username = input('What is your plex.tv username: ')
    password = getpass('What is your plex.tv password: ')
    print(f'Authenticating with Plex.tv as {username}..')
    return MyPlexAccount(username, password)


def createMyPlexDevice(headers, account, timeout=10):  # pragma: no cover
    """ Helper function to create a new MyPlexDevice. Returns a new MyPlexDevice instance.

        Parameters:
            headers (dict): Provide the X-Plex- headers for the new device.
                A unique X-Plex-Client-Identifier is required.
            account (MyPlexAccount): The Plex account to create the device on.
            timeout (int): Timeout in seconds to wait for device login.
    """
    from plexapi.myplex import MyPlexPinLogin

    if 'X-Plex-Client-Identifier' not in headers:
        raise BadRequest('The X-Plex-Client-Identifier header is required.')

    clientIdentifier = headers['X-Plex-Client-Identifier']

    pinlogin = MyPlexPinLogin(headers=headers)
    pinlogin.run(timeout=timeout)
    account.link(pinlogin.pin)
    pinlogin.waitForLogin()

    return account.device(clientId=clientIdentifier)


def plexOAuth(headers, forwardUrl=None, timeout=120):  # pragma: no cover
    """ Helper function for Plex OAuth login. Returns a new MyPlexAccount instance.

        Parameters:
            headers (dict): Provide the X-Plex- headers for the new device.
                A unique X-Plex-Client-Identifier is required.
            forwardUrl (str, optional): The url to redirect the client to after login.
            timeout (int, optional): Timeout in seconds to wait for device login. Default 120 seconds.
    """
    from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

    if 'X-Plex-Client-Identifier' not in headers:
        raise BadRequest('The X-Plex-Client-Identifier header is required.')

    pinlogin = MyPlexPinLogin(headers=headers, oauth=True)
    print('Login to Plex at the following url:')
    print(pinlogin.oauthUrl(forwardUrl))
    pinlogin.run(timeout=timeout)
    pinlogin.waitForLogin()

    if pinlogin.token:
        print('Login successful!')
        return MyPlexAccount(token=pinlogin.token)
    else:
        print('Login failed.')


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
        print(f'  {index}: {name}')
    print()
    # Request choice from the user
    while True:
        try:
            inp = input(f'{msg}: ')
            if any(s in inp for s in (':', '::', '-')):
                idx = slice(*map(lambda x: int(x.strip()) if x.strip() else None, inp.split(':')))
                return items[idx]
            else:
                return items[int(inp)]

        except (ValueError, IndexError):
            pass


def getAgentIdentifier(section, agent):
    """ Return the full agent identifier from a short identifier, name, or confirm full identifier. """
    agents = []
    for ag in section.agents():
        identifiers = [ag.identifier, ag.shortIdentifier, ag.name]
        if agent in identifiers:
            return ag.identifier
        agents += identifiers
    raise NotFound(f"Could not find \"{agent}\" in agents list ({', '.join(agents)})")


def base64str(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def deprecated(message, stacklevel=2):
    def decorator(func):
        """This is a decorator which can be used to mark functions
        as deprecated. It will result in a warning being emitted
        when the function is used."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = f'Call to deprecated function or method "{func.__name__}", {message}.'
            warnings.warn(msg, category=DeprecationWarning, stacklevel=stacklevel)
            log.warning(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def iterXMLBFS(root, tag=None):
    """ Iterate through an XML tree using a breadth-first search.
        If tag is specified, only return nodes with that tag.
    """
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if tag is None or node.tag == tag:
            yield node
        queue.extend(list(node))


def toJson(obj, **kwargs):
    """ Convert an object to a JSON string.

        Parameters:
            obj (object): The object to convert.
            **kwargs (dict): Keyword arguments to pass to ``json.dumps()``.
    """
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
    return json.dumps(obj, default=serialize, **kwargs)


def openOrRead(file):
    if hasattr(file, 'read'):
        return file.read()
    with open(file, 'rb') as f:
        return f.read()


def sha1hash(guid):
    """ Return the SHA1 hash of a guid. """
    return sha1(guid.encode('utf-8')).hexdigest()
