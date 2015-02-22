from .torrent import Torrent

class InvalidTorrentGroupException(Exception):
    pass

class TorrentGroup(object):
    """
    Represents a Torrent Group (usually an album). Note that TorrentGroup.torrents may not be comprehensive if you
    haven't called TorrentGroup.update_group_data()...it may have only been populated with filtered search results.
    Check TorrentGroup.has_complete_torrent_list (boolean) to be sure.
    """
    def __init__(self, id, parent_api):
        self.id = id
        self.parent_api = parent_api
        self.name = None
        self.wiki_body = None
        self.wiki_image = None
        self.year = None
        self.record_label = None
        self.catalogue_number = None
        self.tags = []
        self.release_type = None
        self.vanity_house = None
        self.has_bookmarked = None
        self.category = None
        self.time = None
        self.music_info = None
        self.torrents = []
        self.has_complete_torrent_list = False

        self.parent_api.cached_torrent_groups[self.id] = self

    def update_group_data(self):
        response = self.parent_api.request(action='torrentgroup', id=self.id)
        self.set_group_data(response)

    def set_group_data(self, torrent_group_json_response):
        """
        Takes parsed JSON response from 'torrentgroup' action on api, and updates relevant information.
        To avoid problems, only pass in data from an API call that used this torrentgroup's ID as an argument.
        """
        if self.id != torrent_group_json_response['group']['id']:
            raise InvalidTorrentGroupException("Tried to update a TorrentGroup's information from an 'artist' API call with a different id." +
                                               " Should be %s, got %s" % (self.id, torrent_group_json_response['group']['groupId']) )

        self.name = torrent_group_json_response['group']['name']
        self.year = torrent_group_json_response['group']['year']
        self.wiki_body = torrent_group_json_response['group']['wikiBody']
        self.wiki_image = torrent_group_json_response['group']['wikiImage']
        self.record_label = torrent_group_json_response['group']['recordLabel']
        self.catalogue_number = torrent_group_json_response['group']['catalogueNumber']

        self.release_type = torrent_group_json_response['group']['releaseType']
        self.category = self.parent_api.get_category(torrent_group_json_response['group']['categoryId'],
                                                     torrent_group_json_response['group']['categoryName'])
        self.time = torrent_group_json_response['group']['time']
        self.vanity_house = torrent_group_json_response['group']['vanityHouse']

        self.music_info = torrent_group_json_response['group']['musicInfo']
        self.music_info['artists'] = [ self.parent_api.get_artist(artist['id'], artist['name'])
                                       for artist in self.music_info['artists'] ]
        self.music_info['with'] = [ self.parent_api.get_artist(artist['id'], artist['name'])
                                       for artist in self.music_info['with'] ]

        if 'torrents' in torrent_group_json_response:
            self.torrents = []
            for torrent_dict in torrent_group_json_response['torrents']:
                torrent_dict['groupId'] = self.id
                torrent = self.parent_api.get_torrent(torrent_dict['id'])
                torrent.set_torrent_group_data(torrent_dict)
                self.torrents.append(torrent)
            self.has_complete_torrent_list = True
        elif 'torrent' in torrent_group_json_response:
            torrent = self.parent_api.get_torrent(torrent_group_json_response['torrent']['id'])
            self.torrents.append(torrent)

    def set_artist_group_data(self, artist_group_json_response):
        """
        Takes torrentgroup section from parsed JSON response from 'artist' action on api, and updates relevant information.
        """
        if self.id != artist_group_json_response['groupId']:
            raise InvalidTorrentGroupException("Tried to update a TorrentGroup's information from an 'artist' API call with a different id." +
                               " Should be %s, got %s" % (self.id, artist_group_json_response['groupId']) )

        self.name = artist_group_json_response['groupName']
        self.year = artist_group_json_response['groupYear']
        self.record_label = artist_group_json_response['groupRecordLabel']
        self.catalogue_number = artist_group_json_response['groupCatalogueNumber']

        self.tags = []
        for tag_name in artist_group_json_response['tags']:
            tag = self.parent_api.get_tag(tag_name)
            self.tags.append(tag)

        self.release_type = artist_group_json_response['releaseType']
        self.has_bookmarked = artist_group_json_response['hasBookmarked']

        self.torrents = []
        for torrent_dict in artist_group_json_response['torrent']:
            torrent = self.parent_api.get_torrent(torrent_dict['id'])
            torrent.set_torrent_artist_data(torrent_dict)
            self.torrents.append(torrent)
        self.has_complete_torrent_list = True

    def set_torrent_search_data(self, search_json_response):
        if self.id != search_json_response['groupId']:
            raise InvalidTorrentGroupException("Tried to update a TorrentGroup's information from an 'browse'/search API call with a different id." +
                                       " Should be %s, got %s" % (self.id, search_json_response['groupId']) )

        self.name = search_json_response['groupName']
        # purposefully ignoring search_json_response['artist']...the other data updates don't include it, would just get confusing
        self.tags = []
        for tag_name in search_json_response['tags']:
            tag = self.parent_api.get_tag(tag_name)
            self.tags.append(tag)
        # some of the below keys aren't in things like comics...should probably watch out for this elsewhere
        if 'bookmarked' in search_json_response.keys():
            self.has_bookmarked = search_json_response['bookmarked']
        if 'vanityHouse' in search_json_response.keys():
            self.vanity_house = search_json_response['vanityHouse']
        if 'groupYear' in search_json_response.keys():
            self.year = search_json_response['groupYear']
        if 'releaseType' in search_json_response.keys():
            self.release_type = search_json_response['releaseType']
        self.time = search_json_response['groupTime']
        if 'torrentId' in search_json_response.keys():
            search_json_response['torrents'] = [{'torrentId': search_json_response['torrentId']}]

        new_torrents = []
        for torrent_dict in search_json_response['torrents']:
            torrent_dict['groupId'] = self.id
            torrent = self.parent_api.get_torrent(torrent_dict['torrentId'])
            new_torrents.append(torrent)
        # torrent information gets populated in API search call, no need to duplicate that here
        self.torrents = self.torrents + new_torrents


    def __repr__(self):
        return "TorrentGroup: %s - ID: %s" % (self.name, self.id)
