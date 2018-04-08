# -*- coding: utf-8 -*-
from plexapi import utils
from plexapi.base import PlexObject


class PlayQueue(PlexObject):
    """ Control a PlayQueue.

        Attributes:
            key (str): This is only added to support playMedia
            identifier (str): com.plexapp.plugins.library
            initpath (str): Relative url where data was grabbed from.
            items (list): List of :class:`~plexapi.media.Media` or class:`~plexapi.playlist.Playlist`
            mediaTagPrefix (str): Fx /system/bundle/media/flags/
            mediaTagVersion (str): Fx 1485957738
            playQueueID (str): a id for the playqueue
            playQueueSelectedItemID (str): playQueueSelectedItemID
            playQueueSelectedItemOffset (str): playQueueSelectedItemOffset
            playQueueSelectedMetadataItemID (<type 'str'>): 7
            playQueueShuffled (bool): True if shuffled
            playQueueSourceURI (str): Fx library://150425c9-0d99-4242-821e-e5ab81cd2221/item//library/metadata/7
            playQueueTotalCount (str): How many items in the play queue.
            playQueueVersion (str): What version the playqueue is.
            server (:class:`~plexapi.server.PlexServer`): Server you are connected to.
            size (str): Seems to be a alias for playQueueTotalCount.
    """

    def _loadData(self, data):
        self._data = data
        self.identifier = data.attrib.get('identifier')
        self.mediaTagPrefix = data.attrib.get('mediaTagPrefix')
        self.mediaTagVersion = data.attrib.get('mediaTagVersion')
        self.playQueueID = data.attrib.get('playQueueID')
        self.playQueueSelectedItemID = data.attrib.get('playQueueSelectedItemID')
        self.playQueueSelectedItemOffset = data.attrib.get('playQueueSelectedItemOffset')
        self.playQueueSelectedMetadataItemID = data.attrib.get('playQueueSelectedMetadataItemID')
        self.playQueueShuffled = utils.cast(bool, data.attrib.get('playQueueShuffled', 0))
        self.playQueueSourceURI = data.attrib.get('playQueueSourceURI')
        self.playQueueTotalCount = data.attrib.get('playQueueTotalCount')
        self.playQueueVersion = data.attrib.get('playQueueVersion')
        self.size = utils.cast(int, data.attrib.get('size', 0))
        self.items = self.findItems(data)

    @classmethod
    def create(cls, server, item, shuffle=0, repeat=0, includeChapters=1, includeRelated=1):
        """ Create and returns a new :class:`~plexapi.playqueue.PlayQueue`.

            Paramaters:
                server (:class:`~plexapi.server.PlexServer`): Server you are connected to.
                item (:class:`~plexapi.media.Media` or class:`~plexapi.playlist.Playlist`): A media or Playlist.
                shuffle (int, optional): Start the playqueue shuffled.
                repeat (int, optional): Start the playqueue shuffled.
                includeChapters (int, optional): include Chapters.
                includeRelated (int, optional): include Related.
        """
        args = {}
        args['includeChapters'] = includeChapters
        args['includeRelated'] = includeRelated
        args['repeat'] = repeat
        args['shuffle'] = shuffle
        if item.type == 'playlist':
            args['playlistID'] = item.ratingKey
            args['type'] = item.playlistType
        else:
            uuid = item.section().uuid
            args['key'] = item.key
            args['type'] = item.listType
            args['uri'] = 'library://%s/item/%s' % (uuid, item.key)
        path = '/playQueues%s' % utils.joinArgs(args)
        data = server.query(path, method=server._session.post)
        c = cls(server, data, initpath=path)
        # we manually add a key so we can pass this to playMedia
        # since the data, does not contain a key.
        c.key = item.key
        return c
