"""
Support for discovery using GDM (Good Day Mate), multicast protocol by Plex.

# Licensed Apache 2.0
# From https://github.com/home-assistant/netdisco/netdisco/gdm.py

Inspired by:
  hippojay's plexGDM: https://github.com/hippojay/script.plexbmc.helper/resources/lib/plexgdm.py
  iBaa's PlexConnect: https://github.com/iBaa/PlexConnect/PlexAPI.py
"""
import socket
import struct


class GDM:
    """Base class to discover GDM services.

       Attributes:
           entries (List<dict>): List of server and/or client data discovered.
    """

    def __init__(self):
        self.entries = []

    def scan(self, scan_for_clients=False):
        """Scan the network."""
        self.update(scan_for_clients)

    def all(self, scan_for_clients=False):
        """Return all found entries.

        Will scan for entries if not scanned recently.
        """
        self.scan(scan_for_clients)
        return list(self.entries)

    def find_by_content_type(self, value):
        """Return a list of entries that match the content_type."""
        self.scan()
        return [entry for entry in self.entries
                if value in entry['data']['Content-Type']]

    def find_by_data(self, values):
        """Return a list of entries that match the search parameters."""
        self.scan()
        return [entry for entry in self.entries
                if all(item in entry['data'].items()
                       for item in values.items())]

    def update(self, scan_for_clients):
        """Scan for new GDM services.

        Examples of the dict list assigned to self.entries by this function:

            Server:

                [{'data': {
                     'Content-Type': 'plex/media-server',
                     'Host': '53f4b5b6023d41182fe88a99b0e714ba.plex.direct',
                     'Name': 'myfirstplexserver',
                     'Port': '32400',
                     'Resource-Identifier': '646ab0aa8a01c543e94ba975f6fd6efadc36b7',
                     'Updated-At': '1585769946',
                     'Version': '1.18.8.2527-740d4c206',
                },
                 'from': ('10.10.10.100', 32414)}]

            Clients:

                [{'data': {'Content-Type': 'plex/media-player',
                     'Device-Class': 'stb',
                     'Name': 'plexamp',
                     'Port': '36000',
                     'Product': 'Plexamp',
                     'Protocol': 'plex',
                     'Protocol-Capabilities': 'timeline,playback,playqueues,playqueues-creation',
                     'Protocol-Version': '1',
                     'Resource-Identifier': 'b6e57a3f-e0f8-494f-8884-f4b58501467e',
                     'Version': '1.1.0',
                },
                 'from': ('10.10.10.101', 32412)}]
        """

        gdm_msg = 'M-SEARCH * HTTP/1.0'.encode('ascii')
        gdm_timeout = 1

        self.entries = []
        known_responses = []

        # setup socket for discovery -> multicast message
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(gdm_timeout)

        # Set the time-to-live for messages for local network
        sock.setsockopt(socket.IPPROTO_IP,
                        socket.IP_MULTICAST_TTL,
                        struct.pack("B", gdm_timeout))

        if scan_for_clients:
            # setup socket for broadcast to Plex clients
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            gdm_ip = '255.255.255.255'
            gdm_port = 32412
        else:
            # setup socket for multicast to Plex server(s)
            gdm_ip = '239.0.0.250'
            gdm_port = 32414

        try:
            # Send data to the multicast group
            sock.sendto(gdm_msg, (gdm_ip, gdm_port))

            # Look for responses from all recipients
            while True:
                try:
                    bdata, host = sock.recvfrom(1024)
                    data = bdata.decode('utf-8')
                    if '200 OK' in data.splitlines()[0]:
                        ddata = {k: v.strip() for (k, v) in (
                            line.split(':') for line in
                            data.splitlines() if ':' in line)}
                        identifier = ddata.get('Resource-Identifier')
                        if identifier and identifier in known_responses:
                            continue
                        known_responses.append(identifier)
                        self.entries.append({'data': ddata,
                                             'from': host})
                except socket.timeout:
                    break
        finally:
            sock.close()


def main():
    """Test GDM discovery."""
    from pprint import pprint

    gdm = GDM()

    pprint("Scanning GDM for servers...")
    gdm.scan()
    pprint(gdm.entries)

    pprint("Scanning GDM for clients...")
    gdm.scan(scan_for_clients=True)
    pprint(gdm.entries)


if __name__ == "__main__":
    main()
