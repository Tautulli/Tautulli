import requests
data = requests.get("https://www.crummy.com/").content
from bs4 import _s
data = [x for x in _s(data).block_text()]
