import logging
LOG_FORMAT = ('[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)s] '
                  '[%(funcName)s()] %(message)s')
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
from pprint import pprint
from ipwhois.experimental import bulk_lookup_rdap
from ipwhois import IPWhois
# obj = IPWhois('202.143.89.202')
# result = obj.lookup_rdap(depth=0, root_ent_check=True, inc_raw=False)
# result, stats = bulk_lookup_rdap(['177.104.124.235'])
# pprint(result)
# pprint(stats)

import requests
r = requests.get('https://xn--c79as89aj0e29b77z.xn--3e0b707e/')
print(r)
