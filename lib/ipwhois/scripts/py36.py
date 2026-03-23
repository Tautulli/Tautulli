import urllib.request
import traceback
try:
    local_filename, headers = urllib.request.urlretrieve('https://xn--c79as89aj0e29b77z.xn--3e0b707e/')
except:
    traceback.print_exc()

