class Tag(object):
    def __init__(self, name, parent_api):
        self.name = name
        self.artist_counts = {}
        self.parent_api = parent_api

        self.parent_api.cached_tags[self.name] = self # add self to cache of known Tag objects

    def set_artist_count(self, artist, count):
        """
        Adds an artist to the known list of artists tagged with this tag (if necessary), and sets the count of times
        that that artist has been known to be tagged with this tag.
        """
        self.artist_counts[artist] = count

    def __repr__(self):
        return "Tag: %s" % self.name