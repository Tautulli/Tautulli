from cloudinary import Search


class SearchFolders(Search):
    FOLDERS = 'folders'

    def __init__(self):
        super(SearchFolders, self).__init__()

        self.endpoint(self.FOLDERS)
