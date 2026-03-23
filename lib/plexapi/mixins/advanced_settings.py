from urllib.parse import urlencode

from plexapi import settings
from plexapi.exceptions import NotFound


class AdvancedSettingsMixin:
    """ Mixin for Plex objects that can have advanced settings. """

    def preferences(self):
        """ Returns a list of :class:`~plexapi.settings.Preferences` objects. """
        key = f'{self.key}?includePreferences=1'
        return self.fetchItems(key, cls=settings.Preferences, rtag='Preferences')

    def preference(self, pref):
        """ Returns a :class:`~plexapi.settings.Preferences` object for the specified pref.

            Parameters:
                pref (str): The id of the preference to return.
        """
        prefs = self.preferences()
        try:
            return next(p for p in prefs if p.id == pref)
        except StopIteration:
            availablePrefs = [p.id for p in prefs]
            raise NotFound(f'Unknown preference "{pref}" for {self.TYPE}. '
                           f'Available preferences: {availablePrefs}') from None

    def editAdvanced(self, **kwargs):
        """ Edit a Plex object's advanced settings. """
        data = {}
        key = f'{self.key}/prefs?'
        preferences = {pref.id: pref for pref in self.preferences() if pref.enumValues}
        for settingID, value in kwargs.items():
            try:
                pref = preferences[settingID]
            except KeyError:
                raise NotFound(f'{value} not found in {list(preferences.keys())}')

            enumValues = pref.enumValues
            if enumValues.get(value, enumValues.get(str(value))):
                data[settingID] = value
            else:
                raise NotFound(f'{value} not found in {list(enumValues)}')
        url = key + urlencode(data)
        self._server.query(url, method=self._server._session.put)
        return self

    def defaultAdvanced(self):
        """ Edit all of a Plex object's advanced settings to default. """
        data = {}
        key = f'{self.key}/prefs?'
        for preference in self.preferences():
            data[preference.id] = preference.default
        url = key + urlencode(data)
        self._server.query(url, method=self._server._session.put)
        return self
