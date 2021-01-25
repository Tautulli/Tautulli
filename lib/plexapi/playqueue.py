# -*- coding: utf-8 -*-
from urllib.parse import quote_plus

from plexapi import utils
from plexapi.base import PlexObject
from plexapi.exceptions import BadRequest, Unsupported


class PlayQueue(PlexObject):
    """Control a PlayQueue.

    Attributes:
        TAG (str): 'PlayQueue'
        TYPE (str): 'playqueue'
        identifier (str): com.plexapp.plugins.library
        items (list): List of :class:`~plexapi.media.Media` or :class:`~plexapi.playlist.Playlist`
        mediaTagPrefix (str): Fx /system/bundle/media/flags/
        mediaTagVersion (int): Fx 1485957738
        playQueueID (int): ID of the PlayQueue.
        playQueueLastAddedItemID (int):
            Defines where the "Up Next" region starts. Empty unless PlayQueue is modified after creation.
        playQueueSelectedItemID (int): The queue item ID of the currently selected item.
        playQueueSelectedItemOffset (int):
            The offset of the selected item in the PlayQueue, from the beginning of the queue.
        playQueueSelectedMetadataItemID (int): ID of the currently selected item, matches ratingKey.
        playQueueShuffled (bool): True if shuffled.
        playQueueSourceURI (str): Original URI used to create the PlayQueue.
        playQueueTotalCount (int): How many items in the PlayQueue.
        playQueueVersion (int): Version of the PlayQueue. Increments every time a change is made to the PlayQueue.
        selectedItem (:class:`~plexapi.media.Media`): Media object for the currently selected item.
        _server (:class:`~plexapi.server.PlexServer`): PlexServer associated with the PlayQueue.
        size (int): Alias for playQueueTotalCount.
    """

    TAG = "PlayQueue"
    TYPE = "playqueue"

    def _loadData(self, data):
        self._data = data
        self.identifier = data.attrib.get("identifier")
        self.mediaTagPrefix = data.attrib.get("mediaTagPrefix")
        self.mediaTagVersion = utils.cast(int, data.attrib.get("mediaTagVersion"))
        self.playQueueID = utils.cast(int, data.attrib.get("playQueueID"))
        self.playQueueLastAddedItemID = utils.cast(
            int, data.attrib.get("playQueueLastAddedItemID")
        )
        self.playQueueSelectedItemID = utils.cast(
            int, data.attrib.get("playQueueSelectedItemID")
        )
        self.playQueueSelectedItemOffset = utils.cast(
            int, data.attrib.get("playQueueSelectedItemOffset")
        )
        self.playQueueSelectedMetadataItemID = utils.cast(
            int, data.attrib.get("playQueueSelectedMetadataItemID")
        )
        self.playQueueShuffled = utils.cast(
            bool, data.attrib.get("playQueueShuffled", 0)
        )
        self.playQueueSourceURI = data.attrib.get("playQueueSourceURI")
        self.playQueueTotalCount = utils.cast(
            int, data.attrib.get("playQueueTotalCount")
        )
        self.playQueueVersion = utils.cast(int, data.attrib.get("playQueueVersion"))
        self.size = utils.cast(int, data.attrib.get("size", 0))
        self.items = self.findItems(data)
        self.selectedItem = self[self.playQueueSelectedItemOffset]

    def __getitem__(self, key):
        if not self.items:
            return None
        return self.items[key]

    def __len__(self):
        return self.playQueueTotalCount

    def __iter__(self):
        yield from self.items

    def __contains__(self, media):
        """Returns True if the PlayQueue contains the provided media item."""
        return any(x.playQueueItemID == media.playQueueItemID for x in self.items)

    def getQueueItem(self, item):
        """
        Accepts a media item and returns a similar object from this PlayQueue.
        Useful for looking up playQueueItemIDs using items obtained from the Library.
        """
        matches = [x for x in self.items if x == item]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise BadRequest(
                "{item} occurs multiple times in this PlayQueue, provide exact item".format(item=item)
            )
        else:
            raise BadRequest("{item} not valid for this PlayQueue".format(item=item))

    @classmethod
    def get(
        cls,
        server,
        playQueueID,
        own=False,
        center=None,
        window=50,
        includeBefore=True,
        includeAfter=True,
    ):
        """Retrieve an existing :class:`~plexapi.playqueue.PlayQueue` by identifier.

        Parameters:
            server (:class:`~plexapi.server.PlexServer`): Server you are connected to.
            playQueueID (int): Identifier of an existing PlayQueue.
            own (bool, optional): If server should transfer ownership.
            center (int, optional): The playQueueItemID of the center of the window. Does not change selectedItem.
            window (int, optional): Number of items to return from each side of the center item.
            includeBefore (bool, optional):
                Include items before the center, defaults True. Does not include center if False.
            includeAfter (bool, optional):
                Include items after the center, defaults True. Does not include center if False.
        """
        args = {
            "own": utils.cast(int, own),
            "window": window,
            "includeBefore": utils.cast(int, includeBefore),
            "includeAfter": utils.cast(int, includeAfter),
        }
        if center:
            args["center"] = center

        path = "/playQueues/{playQueueID}{args}".format(playQueueID=playQueueID, args=utils.joinArgs(args))
        data = server.query(path, method=server._session.get)
        c = cls(server, data, initpath=path)
        c._server = server
        return c

    @classmethod
    def create(
        cls,
        server,
        items,
        startItem=None,
        shuffle=0,
        repeat=0,
        includeChapters=1,
        includeRelated=1,
        continuous=0,
    ):
        """Create and return a new :class:`~plexapi.playqueue.PlayQueue`.

        Parameters:
            server (:class:`~plexapi.server.PlexServer`): Server you are connected to.
            items (:class:`~plexapi.media.Media` or :class:`~plexapi.playlist.Playlist`):
                A media item, list of media items, or Playlist.
            startItem (:class:`~plexapi.media.Media`, optional):
                Media item in the PlayQueue where playback should begin.
            shuffle (int, optional): Start the playqueue shuffled.
            repeat (int, optional): Start the playqueue shuffled.
            includeChapters (int, optional): include Chapters.
            includeRelated (int, optional): include Related.
            continuous (int, optional): include additional items after the initial item.
                For a show this would be the next episodes, for a movie it does nothing.
        """
        args = {
            "includeChapters": includeChapters,
            "includeRelated": includeRelated,
            "repeat": repeat,
            "shuffle": shuffle,
            "continuous": continuous,
        }

        if isinstance(items, list):
            item_keys = ",".join([str(x.ratingKey) for x in items])
            uri_args = quote_plus("/library/metadata/{item_keys}".format(item_keys=item_keys))
            args["uri"] = "library:///directory/{uri_args}".format(uri_args=uri_args)
            args["type"] = items[0].listType
        elif items.type == "playlist":
            args["playlistID"] = items.ratingKey
            args["type"] = items.playlistType
        else:
            uuid = items.section().uuid
            args["type"] = items.listType
            args["uri"] = "library://{uuid}/item/{key}".format(uuid=uuid, key=items.key)

        if startItem:
            args["key"] = startItem.key

        path = "/playQueues{args}".format(args=utils.joinArgs(args))
        data = server.query(path, method=server._session.post)
        c = cls(server, data, initpath=path)
        c.playQueueType = args["type"]
        c._server = server
        return c

    def addItem(self, item, playNext=False, refresh=True):
        """
        Append the provided item to the "Up Next" section of the PlayQueue.
        Items can only be added to the section immediately following the current playing item.

        Parameters:
            item (:class:`~plexapi.media.Media` or :class:`~plexapi.playlist.Playlist`): Single media item or Playlist.
            playNext (bool, optional): If True, add this item to the front of the "Up Next" section.
                If False, the item will be appended to the end of the "Up Next" section.
                Only has an effect if an item has already been added to the "Up Next" section.
                See https://support.plex.tv/articles/202188298-play-queues/ for more details.
            refresh (bool, optional): Refresh the PlayQueue from the server before updating.
        """
        if refresh:
            self.refresh()

        args = {}
        if item.type == "playlist":
            args["playlistID"] = item.ratingKey
            itemType = item.playlistType
        else:
            uuid = item.section().uuid
            itemType = item.listType
            args["uri"] = "library://{uuid}/item{key}".format(uuid=uuid, key=item.key)

        if itemType != self.playQueueType:
            raise Unsupported("Item type does not match PlayQueue type")

        if playNext:
            args["next"] = 1

        path = "/playQueues/{playQueueID}{args}".format(playQueueID=self.playQueueID, args=utils.joinArgs(args))
        data = self._server.query(path, method=self._server._session.put)
        self._loadData(data)

    def moveItem(self, item, after=None, refresh=True):
        """
        Moves an item to the beginning of the PlayQueue.  If `after` is provided,
        the item will be placed immediately after the specified item.

        Parameters:
            item (:class:`~plexapi.base.Playable`): An existing item in the PlayQueue to move.
            afterItemID (:class:`~plexapi.base.Playable`, optional): A different item in the PlayQueue.
                If provided, `item` will be placed in the PlayQueue after this item.
            refresh (bool, optional): Refresh the PlayQueue from the server before updating.
        """
        args = {}

        if refresh:
            self.refresh()

        if item not in self:
            item = self.getQueueItem(item)

        if after:
            if after not in self:
                after = self.getQueueItem(after)
            args["after"] = after.playQueueItemID

        path = "/playQueues/{playQueueID}/items/{playQueueItemID}/move{args}".format(
            playQueueID=self.playQueueID, playQueueItemID=item.playQueueItemID, args=utils.joinArgs(args)
        )
        data = self._server.query(path, method=self._server._session.put)
        self._loadData(data)

    def removeItem(self, item, refresh=True):
        """Remove an item from the PlayQueue.

        Parameters:
            item (:class:`~plexapi.base.Playable`): An existing item in the PlayQueue to move.
            refresh (bool, optional): Refresh the PlayQueue from the server before updating.
        """
        if refresh:
            self.refresh()

        if item not in self:
            item = self.getQueueItem(item)

        path = "/playQueues/{playQueueID}/items/{playQueueItemID}".format(
            playQueueID=self.playQueueID, playQueueItemID=item.playQueueItemID
        )
        data = self._server.query(path, method=self._server._session.delete)
        self._loadData(data)

    def clear(self):
        """Remove all items from the PlayQueue."""
        path = "/playQueues/{playQueueID}/items".format(playQueueID=self.playQueueID)
        data = self._server.query(path, method=self._server._session.delete)
        self._loadData(data)

    def refresh(self):
        """Refresh the PlayQueue from the Plex server."""
        path = "/playQueues/{playQueueID}".format(playQueueID=self.playQueueID)
        data = self._server.query(path, method=self._server._session.get)
        self._loadData(data)
