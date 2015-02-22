ALBUM = "Album"
SOUNDTRACK = "Soundtrack"
EP = "EP"
ANTHOLOGY = "Anthology"
COMPILATION = "Compilation"
DJ_MIX = "DJ Mix"
SINGLE = "Single"
LIVE_ALBUM = "Live album"
REMIX = "Remix"
BOOTLEG = "Bootleg"
INTERVIEW = "Interview"
MIXTAPE = "Mixtape"
UNKNOWN = "Unknown"

ALL_RELEASE_TYPES = [ALBUM, SOUNDTRACK, EP, ANTHOLOGY, COMPILATION, DJ_MIX, SINGLE, LIVE_ALBUM, REMIX, BOOTLEG,
                     INTERVIEW, MIXTAPE, UNKNOWN]

def get_int_val(release_type):
    return ALL_RELEASE_TYPES.index(release_type) + 1