from HTMLParser import HTMLParser
import re

class InvalidTorrentException(Exception):
    pass

class Torrent(object):
    def __init__(self, id, parent_api):
        self.id = id
        self.parent_api = parent_api
        self.group = None
        self.media = None
        self.format = None
        self.encoding = None
        self.remaster_year = None
        self.remastered = None
        self.remaster_title = None
        self.remaster_record_label = None
        self.remaster_catalogue_number = None
        self.scene = None
        self.has_log = None
        self.has_cue = None
        self.log_score = None
        self.file_count = None
        self.free_torrent = None
        self.size = None
        self.leechers = None
        self.seeders = None
        self.snatched = None
        self.time = None
        self.has_file = None
        self.description = None
        self.file_list = []
        self.file_path = None
        self.user = None

        self.parent_api.cached_torrents[self.id] = self

    def set_torrent_complete_data(self, torrent_json_response):
        if self.id != torrent_json_response['torrent']['id']:
            raise InvalidTorrentException("Tried to update a Torrent's information from an 'artist' API call with a different id." +
                                       " Should be %s, got %s" % (self.id, torrent_json_response['id']) )

        self.group = self.parent_api.get_torrent_group(torrent_json_response['group']['id'])
        had_complete_list = self.group.has_complete_torrent_list
        self.group.set_group_data(torrent_json_response)
        self.group.has_complete_torrent_list = had_complete_list

        self.media = torrent_json_response['torrent']['media']
        self.format = torrent_json_response['torrent']['format']
        self.encoding = torrent_json_response['torrent']['encoding']
        self.remaster_year = torrent_json_response['torrent']['remasterYear']
        self.remastered = torrent_json_response['torrent']['remastered']
        self.remaster_title = torrent_json_response['torrent']['remasterTitle']
        self.remaster_record_label = torrent_json_response['torrent']['remasterRecordLabel']
        self.scene = torrent_json_response['torrent']['scene']
        self.has_log = torrent_json_response['torrent']['hasLog']
        self.has_cue = torrent_json_response['torrent']['hasCue']
        self.log_score = torrent_json_response['torrent']['logScore']
        self.file_count = torrent_json_response['torrent']['fileCount']
        self.free_torrent = torrent_json_response['torrent']['freeTorrent']
        self.size = torrent_json_response['torrent']['size']
        self.leechers = torrent_json_response['torrent']['leechers']
        self.seeders = torrent_json_response['torrent']['seeders']
        self.snatched = torrent_json_response['torrent']['snatched']
        self.time = torrent_json_response['torrent']['time']
        self.description = torrent_json_response['torrent']['description']
        self.file_list = [ re.match("(.+){{{(\d+)}}}", item).groups()
                           for item in torrent_json_response['torrent']['fileList'].split("|||") ] # tuple ( filename, filesize )
        self.file_path = torrent_json_response['torrent']['filePath']
        self.user = self.parent_api.get_user(torrent_json_response['torrent']['userId'])

    def set_torrent_artist_data(self, artist_torrent_json_response):
        if self.id != artist_torrent_json_response['id']:
            raise InvalidTorrentException("Tried to update a Torrent's information from an 'artist' API call with a different id." +
                                       " Should be %s, got %s" % (self.id, artist_torrent_json_response['id']) )

        self.group = self.parent_api.get_torrent_group(artist_torrent_json_response['groupId'])
        self.media = artist_torrent_json_response['media']
        self.format = artist_torrent_json_response['format']
        self.encoding = artist_torrent_json_response['encoding']
        self.remaster_year = artist_torrent_json_response['remasterYear']
        self.remastered = artist_torrent_json_response['remastered']
        self.remaster_title = artist_torrent_json_response['remasterTitle']
        self.remaster_record_label = artist_torrent_json_response['remasterRecordLabel']
        self.scene = artist_torrent_json_response['scene']
        self.has_log = artist_torrent_json_response['hasLog']
        self.has_cue = artist_torrent_json_response['hasCue']
        self.log_score = artist_torrent_json_response['logScore']
        self.file_count = artist_torrent_json_response['fileCount']
        self.free_torrent = artist_torrent_json_response['freeTorrent']
        self.size = artist_torrent_json_response['size']
        self.leechers = artist_torrent_json_response['leechers']
        self.seeders = artist_torrent_json_response['seeders']
        self.snatched = artist_torrent_json_response['snatched']
        self.time = artist_torrent_json_response['time']
        self.has_file = artist_torrent_json_response['hasFile']

    def set_torrent_group_data(self, group_torrent_json_response):
        if self.id != group_torrent_json_response['id']:
            raise InvalidTorrentException("Tried to update a Torrent's information from a 'torrentgroup' API call with a different id." +
                                          " Should be %s, got %s" % (self.id, group_torrent_json_response['id']) )

        self.group = self.parent_api.get_torrent_group(group_torrent_json_response['groupId'])
        self.media = group_torrent_json_response['media']
        self.format = group_torrent_json_response['format']
        self.encoding = group_torrent_json_response['encoding']
        self.remastered = group_torrent_json_response['remastered']
        self.remaster_year = group_torrent_json_response['remasterYear']
        self.remaster_title = group_torrent_json_response['remasterTitle']
        self.remaster_record_label = group_torrent_json_response['remasterRecordLabel']
        self.remaster_catalogue_number = group_torrent_json_response['remasterCatalogueNumber']
        self.scene = group_torrent_json_response['scene']
        self.has_log = group_torrent_json_response['hasLog']
        self.has_cue = group_torrent_json_response['hasCue']
        self.log_score = group_torrent_json_response['logScore']
        self.file_count = group_torrent_json_response['fileCount']
        self.size = group_torrent_json_response['size']
        self.seeders = group_torrent_json_response['seeders']
        self.leechers = group_torrent_json_response['leechers']
        self.snatched = group_torrent_json_response['snatched']
        self.free_torrent = group_torrent_json_response['freeTorrent']
        self.time = group_torrent_json_response['time']
        self.description = group_torrent_json_response['description']
        self.file_list = [ re.match("(.+){{{(\d+)}}}", item).groups()
                           for item in group_torrent_json_response['fileList'].split("|||") ] # tuple ( filename, filesize )
        self.file_path = group_torrent_json_response['filePath']
        self.user = self.parent_api.get_user(group_torrent_json_response['userId'])

    def set_torrent_search_data(self, search_torrent_json_response):
        if self.id != search_torrent_json_response['torrentId']:
            raise InvalidTorrentException("Tried to update a Torrent's information from a 'browse'/search API call with a different id." +
                                  " Should be %s, got %s" % (self.id, search_torrent_json_response['torrentId']) )

        # TODO: Add conditionals to handle torrents that aren't music
        self.group = self.parent_api.get_torrent_group(search_torrent_json_response['groupId'])
        self.remastered = search_torrent_json_response['remastered']
        self.remaster_year = search_torrent_json_response['remasterYear']
        self.remaster_title = search_torrent_json_response['remasterTitle']
        self.remaster_catalogue_number = search_torrent_json_response['remasterCatalogueNumber']
        self.media = search_torrent_json_response['media']
        self.format = search_torrent_json_response['format']
        self.encoding = search_torrent_json_response['encoding']
        self.has_log = search_torrent_json_response['hasLog']
        self.has_cue = search_torrent_json_response['hasCue']
        self.log_score = search_torrent_json_response['logScore']
        self.scene = search_torrent_json_response['scene']
        self.file_count = search_torrent_json_response['fileCount']
        self.size = search_torrent_json_response['size']
        self.seeders = search_torrent_json_response['seeders']
        self.leechers = search_torrent_json_response['leechers']
        self.snatched = search_torrent_json_response['snatches']
        self.free_torrent = search_torrent_json_response['isFreeleech'] or search_torrent_json_response['isPersonalFreeleech']
        self.time = search_torrent_json_response['time']

    def set_torrent_top_10_data(self, top_10_json_response):
        if self.id != top_10_json_response['torrentId']:
            raise InvalidTorrentException("Tried to update a Torrent's information from a 'browse'/search API call with a different id." +
                                          " Should be %s, got %s" % (self.id, top_10_json_response['torrentId']) )

        # TODO: Add conditionals to handle torrents that aren't music
        self.group = self.parent_api.get_torrent_group(top_10_json_response['groupId'])
        self.group.name = top_10_json_response['groupName']
        if not self.group.music_info and top_10_json_response['artist']:
            self.group.music_info = {'artists': [self.parent_api.get_artist(name=HTMLParser().unescape(top_10_json_response['artist']))]}
        self.remaster_title = top_10_json_response['remasterTitle']
        self.media = top_10_json_response['media']
        self.format = top_10_json_response['format']
        self.encoding = top_10_json_response['encoding']
        self.has_log = top_10_json_response['hasLog']
        self.has_cue = top_10_json_response['hasCue']
        self.scene = top_10_json_response['scene']
        self.seeders = top_10_json_response['seeders']
        self.leechers = top_10_json_response['leechers']
        self.snatched = top_10_json_response['snatched']


    def __repr__(self):
        if self.group:
            groupname = self.group.name
        else:
            groupname = "Unknown Group"
        return "Torrent: %s - %s - ID: %s" % (groupname, self.encoding, self.id)
