# -*- coding: utf-8 -*-
import requests
from plexapi import utils
from plexapi.exceptions import NotFound


class SyncItem(object):
    """ Sync Item. This doesn't current work. """
    def __init__(self, device, data, servers=None):
        self._device = device
        self._servers = servers
        self._loadData(data)

    def _loadData(self, data):
        self._data = data
        self.id = utils.cast(int, data.attrib.get('id'))
        self.version = utils.cast(int, data.attrib.get('version'))
        self.rootTitle = data.attrib.get('rootTitle')
        self.title = data.attrib.get('title')
        self.metadataType = data.attrib.get('metadataType')
        self.machineIdentifier = data.find('Server').get('machineIdentifier')
        self.status = data.find('Status').attrib.copy()
        self.MediaSettings = data.find('MediaSettings').attrib.copy()
        self.policy = data.find('Policy').attrib.copy()
        self.location = data.find('Location').attrib.copy()

    def server(self):
        server = list(filter(lambda x: x.machineIdentifier == self.machineIdentifier, self._servers))
        if 0 == len(server):
            raise NotFound('Unable to find server with uuid %s' % self.machineIdentifier)
        return server[0]

    def getMedia(self):
        server = self.server().connect()
        key = '/sync/items/%s' % self.id
        return server.fetchItems(key)

    def markAsDone(self, sync_id):
        server = self.server().connect()
        url = '/sync/%s/%s/files/%s/downloaded' % (
            self._device.clientIdentifier, server.machineIdentifier, sync_id)
        server.query(url, method=requests.put)
