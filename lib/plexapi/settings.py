# -*- coding: utf-8 -*-
from collections import defaultdict
from urllib.parse import quote

from plexapi import log, utils
from plexapi.base import PlexObject
from plexapi.exceptions import BadRequest, NotFound


class Settings(PlexObject):
    """ Container class for all settings. Allows getting and setting PlexServer settings.

        Attributes:
            key (str): '/:/prefs'
    """
    key = '/:/prefs'

    def __init__(self, server, data, initpath=None):
        self._settings = {}
        super(Settings, self).__init__(server, data, initpath)

    def __getattr__(self, attr):
        if attr.startswith('_'):
            try:
                return self.__dict__[attr]
            except KeyError:
                raise AttributeError
        return self.get(attr).value

    def __setattr__(self, attr, value):
        if not attr.startswith('_'):
            return self.get(attr).set(value)
        self.__dict__[attr] = value

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._data = data
        for elem in data:
            id = utils.lowerFirst(elem.attrib['id'])
            if id in self._settings:
                self._settings[id]._loadData(elem)
                continue
            self._settings[id] = Setting(self._server, elem, self._initpath)

    def all(self):
        """ Returns a list of all :class:`~plexapi.settings.Setting` objects available. """
        return list(v for id, v in sorted(self._settings.items()))

    def get(self, id):
        """ Return the :class:`~plexapi.settings.Setting` object with the specified id. """
        id = utils.lowerFirst(id)
        if id in self._settings:
            return self._settings[id]
        raise NotFound('Invalid setting id: %s' % id)

    def groups(self):
        """ Returns a dict of lists for all :class:`~plexapi.settings.Setting`
            objects grouped by setting group.
        """
        groups = defaultdict(list)
        for setting in self.all():
            groups[setting.group].append(setting)
        return dict(groups)

    def group(self, group):
        """ Return a list of all :class:`~plexapi.settings.Setting` objects in the specified group.

            Parameters:
                group (str): Group to return all settings.
        """
        return self.groups().get(group, [])

    def save(self):
        """ Save any outstanding settnig changes to the :class:`~plexapi.server.PlexServer`. This
            performs a full reload() of Settings after complete.
        """
        params = {}
        for setting in self.all():
            if setting._setValue:
                log.info('Saving PlexServer setting %s = %s' % (setting.id, setting._setValue))
                params[setting.id] = quote(setting._setValue)
        if not params:
            raise BadRequest('No setting have been modified.')
        querystr = '&'.join(['%s=%s' % (k, v) for k, v in params.items()])
        url = '%s?%s' % (self.key, querystr)
        self._server.query(url, self._server._session.put)
        self.reload()


class Setting(PlexObject):
    """ Represents a single Plex setting.

        Attributes:
            id (str): Setting id (or name).
            label (str): Short description of what this setting is.
            summary (str): Long description of what this setting is.
            type (str): Setting type (text, int, double, bool).
            default (str): Default value for this setting.
            value (str,bool,int,float): Current value for this setting.
            hidden (bool): True if this is a hidden setting.
            advanced (bool): True if this is an advanced setting.
            group (str): Group name this setting is categorized as.
            enumValues (list,dict): List or dictionary of valis values for this setting.
    """
    _bool_cast = lambda x: True if x == 'true' or x == '1' else False
    _bool_str = lambda x: str(x).lower()
    TYPES = {
        'bool': {'type': bool, 'cast': _bool_cast, 'tostr': _bool_str},
        'double': {'type': float, 'cast': float, 'tostr': str},
        'int': {'type': int, 'cast': int, 'tostr': str},
        'text': {'type': str, 'cast': str, 'tostr': str},
    }

    def _loadData(self, data):
        """ Load attribute values from Plex XML response. """
        self._setValue = None
        self.id = data.attrib.get('id')
        self.label = data.attrib.get('label')
        self.summary = data.attrib.get('summary')
        self.type = data.attrib.get('type')
        self.default = self._cast(data.attrib.get('default'))
        self.value = self._cast(data.attrib.get('value'))
        self.hidden = utils.cast(bool, data.attrib.get('hidden'))
        self.advanced = utils.cast(bool, data.attrib.get('advanced'))
        self.group = data.attrib.get('group')
        self.enumValues = self._getEnumValues(data)

    def _cast(self, value):
        """ Cast the specific value to the type of this setting. """
        if self.type != 'enum':
            value = utils.cast(self.TYPES.get(self.type)['cast'], value)
        return value

    def _getEnumValues(self, data):
        """ Returns a list of dictionary of valis value for this setting. """
        enumstr = data.attrib.get('enumValues')
        if not enumstr:
            return None
        if ':' in enumstr:
            return {self._cast(k): v for k, v in [kv.split(':') for kv in enumstr.split('|')]}
        return enumstr.split('|')

    def set(self, value):
        """ Set a new value for this setitng. NOTE: You must call plex.settings.save() for before
            any changes to setting values are persisted to the :class:`~plexapi.server.PlexServer`.
        """
        # check a few things up front
        if not isinstance(value, self.TYPES[self.type]['type']):
            badtype = type(value).__name__
            raise BadRequest('Invalid value for %s: a %s is required, not %s' % (self.id, self.type, badtype))
        if self.enumValues and value not in self.enumValues:
            raise BadRequest('Invalid value for %s: %s not in %s' % (self.id, value, list(self.enumValues)))
        # store value off to the side until we call settings.save()
        tostr = self.TYPES[self.type]['tostr']
        self._setValue = tostr(value)

    def toUrl(self):
        """Helper for urls"""
        return '%s=%s' % (self.id, self._value or self.value)


@utils.registerPlexObject
class Preferences(Setting):
    """ Represents a single Preferences.

        Attributes:
            TAG (str): 'Preferences'
            FILTER (str): 'preferences'
    """
    TAG = 'Preferences'
    FILTER = 'preferences'

    def _default(self):
        """ Set the default value for this setting."""
        key = '%s/prefs?' % self._initpath
        url = key + '%s=%s' % (self.id, self.default)
        self._server.query(url, method=self._server._session.put)
