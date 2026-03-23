# Copyright (c) 2013-2024 Philip Hane
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# TODO: Add '_links' for RFC/other references

HR_ASN = {
    'asn': {
        '_short': 'ASN',
        '_name': 'Autonomous System Number',
        '_description': 'Globally unique identifier used for routing '
                        'information exchange with Autonomous Systems.'
    },
    'asn_cidr': {
        '_short': 'ASN CIDR Block',
        '_name': 'ASN Classless Inter-Domain Routing Block',
        '_description': 'Network routing block assigned to an ASN.'
    },
    'asn_country_code': {
        '_short': 'ASN Country Code',
        '_name': 'ASN Assigned Country Code',
        '_description': 'ASN assigned country code in ISO 3166-1 format.'
    },
    'asn_date': {
        '_short': 'ASN Date',
        '_name': 'ASN Allocation Date',
        '_description': 'ASN allocation date in ISO 8601 format.'
    },
    'asn_registry': {
        '_short': 'ASN Registry',
        '_name': 'ASN Assigned Registry',
        '_description': 'ASN assigned regional internet registry.'
    },
    'asn_description': {
        '_short': 'ASN Description',
        '_name': 'ASN Description',
        '_description': 'A brief description for the assigned ASN.'
    }
}

HR_ASN_ORIGIN = {
    'nets': {
        '_short': 'Network',
        '_name': 'ASN Network',
        '_description': 'A network associated with an Autonomous System Number'
                        ' (ASN)',
        'cidr': {
            '_short': 'CIDR',
            '_name': 'Classless Inter-Domain Routing Block',
            '_description': 'The network routing block.'
        },
        'description': {
            '_short': 'Description',
            '_name': 'Description',
            '_description': 'Description for the registered network.'
        },
        'maintainer': {
            '_short': 'Maintainer',
            '_name': 'Maintainer',
            '_description': 'The entity that maintains the network.'
        },
        'updated': {
            '_short': 'Updated',
            '_name': 'Updated Timestamp',
            '_description': 'Network registration updated information.'
        },
        'source': {
            '_short': 'Source',
            '_name': 'ASN Network Information Source',
            '_description': 'The source of the network information.'
        }
    }
}

HR_RDAP_COMMON = {
    'entities': {
        '_short': 'Entities',
        '_name': 'RIR Object Entities',
        '_description': 'List of object names referenced by an RIR object.'
    },
    'events': {
        '_short': 'Events',
        '_name': 'Events',
        '_description': 'Events for an RIR object.',
        'action': {
            '_short': 'Action',
            '_name': 'Event Action (Reason)',
            '_description': 'The reason for an event.'
        },
        'timestamp': {
            '_short': 'Timestamp',
            '_name': 'Event Timestamp',
            '_description': 'The date an event occured in ISO 8601 '
                            'format.'
        },
        'actor': {
            '_short': 'Actor',
            '_name': 'Event Actor',
            '_description': 'The identifier for an event initiator.'
        }
    },
    'handle': {
        '_short': 'Handle',
        '_name': 'RIR Handle',
        '_description': 'Unique identifier for a registered object.'
    },
    'links': {
        '_short': 'Links',
        '_name': 'Links',
        '_description': 'HTTP/HTTPS links provided for an RIR object.'
    },
    'notices': {
        '_short': 'Notices',
        '_name': 'Notices',
        '_description': 'Notices for an RIR object.',
        'description': {
            '_short': 'Description',
            '_name': 'Notice Description',
            '_description': 'The description/body of a notice.'
        },
        'title': {
            '_short': 'Title',
            '_name': 'Notice Title',
            '_description': 'The title/header for a notice.'
        },
        'links': {
            '_short': 'Links',
            '_name': 'Notice Links',
            '_description': 'HTTP/HTTPS links provided for a notice.'
        }
    },
    'remarks': {
        '_short': 'Remarks',
        '_name': 'Remarks',
        '_description': 'Remarks for an RIR object.',
        'description': {
            '_short': 'Description',
            '_name': 'Remark Description',
            '_description': 'The description/body of a remark.'
        },
        'title': {
            '_short': 'Title',
            '_name': 'Remark Title',
            '_description': 'The title/header for a remark.'
        },
        'links': {
            '_short': 'Links',
            '_name': 'Remark Links',
            '_description': 'HTTP/HTTPS links provided for a remark.'
        }
    },
    'status': {
        '_short': 'Status',
        '_name': 'Object Status',
        '_description': 'List indicating the state of a registered object.'
    }
}

HR_RDAP = {
    'network': {
        '_short': 'Network',
        '_name': 'RIR Network',
        '_description': 'The assigned network for an IP address.',
        'cidr': {
            '_short': 'CIDR Block',
            '_name': 'Classless Inter-Domain Routing Block',
            '_description': 'Network routing block an IP address belongs to.'
        },
        'country': {
            '_short': 'Country Code',
            '_name': 'Country Code',
            '_description': 'Country code registered with the RIR in '
                            'ISO 3166-1 format.'
        },
        'end_address': {
            '_short': 'End Address',
            '_name': 'Ending IP Address',
            '_description': 'The last IP address in a network block.'
        },
        'events': HR_RDAP_COMMON['events'],
        'handle': HR_RDAP_COMMON['handle'],
        'ip_version': {
            '_short': 'IP Version',
            '_name': 'IP Protocol Version',
            '_description': 'The IP protocol version (v4 or v6) of an IP '
                            'address.'
        },
        'links': HR_RDAP_COMMON['links'],
        'name': {
            '_short': 'Name',
            '_name': 'RIR Network Name',
            '_description': 'The identifier assigned to the network '
                            'registration for an IP address.'
        },
        'notices': HR_RDAP_COMMON['notices'],
        'parent_handle': {
            '_short': 'Parent Handle',
            '_name': 'RIR Parent Handle',
            '_description': 'Unique identifier for the parent network of '
                            'a registered network.'
        },
        'remarks': HR_RDAP_COMMON['remarks'],
        'start_address': {
            '_short': 'Start Address',
            '_name': 'Starting IP Address',
            '_description': 'The first IP address in a network block.'
        },
        'status': HR_RDAP_COMMON['status'],
        'type': {
            '_short': 'Type',
            '_name': 'RIR Network Type',
            '_description': 'The RIR classification of a registered network.'
        }
    },
    'entities': HR_RDAP_COMMON['entities'],
    'objects': {
        '_short': 'Objects',
        '_name': 'RIR Objects',
        '_description': 'The objects (entities) referenced by an RIR network.',
        'contact': {
            '_short': 'Contact',
            '_name': 'Contact Information',
            '_description': 'Contact information registered with an RIR '
                            'object.',
            'address': {
                '_short': 'Address',
                '_name': 'Postal Address',
                '_description': 'The contact postal address.'
            },
            'email': {
                '_short': 'Email',
                '_name': 'Email Address',
                '_description': 'The contact email address.'
            },
            'kind': {
                '_short': 'Kind',
                '_name': 'Kind',
                '_description': 'The contact information kind (individual, '
                                'group, org, etc).'
            },
            'name': {
                '_short': 'Name',
                '_name': 'Name',
                '_description': 'The contact name.'
            },
            'phone': {
                '_short': 'Phone',
                '_name': 'Phone Number',
                '_description': 'The contact phone number.'
            },
            'role': {
                '_short': 'Role',
                '_name': 'Role',
                '_description': 'The contact\'s role.'
            },
            'title': {
                '_short': 'Title',
                '_name': 'Title',
                '_description': 'The contact\'s position or job title.'
            }
        },
        'entities': HR_RDAP_COMMON['entities'],
        'events': HR_RDAP_COMMON['events'],
        'events_actor': {
            '_short': 'Events Misc',
            '_name': 'Events w/o Actor',
            '_description': 'An event for an RIR object with no event actor.',
            'action': {
                '_short': 'Action',
                '_name': 'Event Action (Reason)',
                '_description': 'The reason for an event.'
            },
            'timestamp': {
                '_short': 'Timestamp',
                '_name': 'Event Timestamp',
                '_description': 'The date an event occured in ISO 8601 '
                                'format.'
            }
        },
        'handle': HR_RDAP_COMMON['handle'],
        'links': HR_RDAP_COMMON['links'],
        'notices': HR_RDAP_COMMON['notices'],
        'remarks': HR_RDAP_COMMON['remarks'],
        'roles': {
            '_short': 'Roles',
            '_name': 'Roles',
            '_description': 'List of roles assigned to a registered object.'
        },
        'status': HR_RDAP_COMMON['status'],
    }
}

HR_WHOIS = {
    'nets': {
        '_short': 'Network',
        '_name': 'RIR Network',
        '_description': 'The assigned network for an IP address. May be a '
                        'parent or child network.',
        'address': {
            '_short': 'Address',
            '_name': 'Postal Address',
            '_description': 'The contact postal address.'
        },
        'cidr': {
            '_short': 'CIDR Blocks',
            '_name': 'Classless Inter-Domain Routing Blocks',
            '_description': 'Network routing blocks an IP address belongs to.'
        },
        'city': {
            '_short': 'City',
            '_name': 'City',
            '_description': 'The city registered with a whois network.'
        },
        'country': {
            '_short': 'Country Code',
            '_name': 'Country Code',
            '_description': 'Country code registered for the network in '
                            'ISO 3166-1 format.'
        },
        'created': {
            '_short': 'Created',
            '_name': 'Created Timestamp',
            '_description': 'The date the network was created in ISO 8601 '
                            'format.'
        },
        'description': {
            '_short': 'Description',
            '_name': 'Description',
            '_description': 'The description for the network.'
        },
        'emails': {
            '_short': 'Emails',
            '_name': 'Email Addresses',
            '_description': 'The contact email addresses.'
        },
        'handle': {
            '_short': 'Handle',
            '_name': 'RIR Network Handle',
            '_description': 'Unique identifier for a registered network.'
        },
        'name': {
            '_short': 'Name',
            '_name': 'RIR Network Name',
            '_description': 'The identifier assigned to the network '
                            'registration for an IP address.'
        },
        'postal_code': {
            '_short': 'Postal',
            '_name': 'Postal Code',
            '_description': 'The postal code registered with a whois network.'
        },
        'range': {
            '_short': 'Ranges',
            '_name': 'CIDR Block Ranges',
            '_description': 'Network routing blocks an IP address belongs to.'
        },
        'state': {
            '_short': 'State',
            '_name': 'State',
            '_description': 'The state registered with a whois network.'
        },
        'updated': {
            '_short': 'Updated',
            '_name': 'Updated Timestamp',
            '_description': 'The date the network was updated in ISO 8601 '
                            'format.'
        }
    },
    'referral': {
        '_short': 'Referral',
        '_name': 'Referral Whois',
        '_description': 'The referral whois data if referenced and enabled.',
    }
}

HR_WHOIS_NIR = {
    'nets': {
        '_short': 'NIR Network',
        '_name': 'National Internet Registry Network',
        '_description': 'The assigned NIR (JPNIC, KRNIC) network for an IP '
                        'address. May be a parent or child network.',
        'address': {
            '_short': 'Address',
            '_name': 'Postal Address',
            '_description': 'The network contact postal address.'
        },
        'cidr': {
            '_short': 'CIDR Blocks',
            '_name': 'Classless Inter-Domain Routing Blocks',
            '_description': 'Network routing blocks an IP address belongs to.'
        },
        'country': {
            '_short': 'Country Code',
            '_name': 'Country Code',
            '_description': 'Country code registered for the network in '
                            'ISO 3166-1 format.'
        },
        'handle': {
            '_short': 'Handle',
            '_name': 'NIR Network Handle',
            '_description': 'Unique identifier for a registered NIR network.'
        },
        'name': {
            '_short': 'Name',
            '_name': 'NIR Network Name',
            '_description': 'The identifier assigned to the network '
                            'registration for an IP address.'
        },
        'postal_code': {
            '_short': 'Postal',
            '_name': 'Postal Code',
            '_description': 'The postal code registered with a NIR network.'
        },
        'range': {
            '_short': 'Ranges',
            '_name': 'CIDR Block Ranges',
            '_description': 'Network routing blocks an IP address belongs to.'
        },
        'nameservers': {
            '_short': 'NS',
            '_name': 'Nameservers',
            '_description': 'Nameservers associated with a NIR network.'
        },
        'created': {
            '_short': 'Created',
            '_name': 'Created Timestamp',
            '_description': 'The date the network was created in ISO 8601 '
                            'format.'
        },
        'updated': {
            '_short': 'Updated',
            '_name': 'Updated Timestamp',
            '_description': 'The date the network was updated in ISO 8601 '
                            'format.'
        },
        'contacts': {
            '_short': 'Contacts',
            '_name': 'NIR Contacts',
            '_description': 'The contacts (admin, tech) registered with a NIR '
                            'network.',
            'organization': {
                '_short': 'Org',
                '_name': 'Organization',
                '_description': 'The contact organization.'
            },
            'division': {
                '_short': 'Div',
                '_name': 'Division',
                '_description': 'The contact division of the organization.'
            },
            'name': {
                '_short': 'Name',
                '_name': 'Name',
                '_description': 'The contact name.'
            },
            'title': {
                '_short': 'Title',
                '_name': 'Title',
                '_description': 'The contact position or job title.'
            },
            'phone': {
                '_short': 'Phone',
                '_name': 'Phone Number',
                '_description': 'The contact phone number.'
            },
            'fax': {
                '_short': 'Fax',
                '_name': 'Fax Number',
                '_description': 'The contact fax number.'
            },
            'email': {
                '_short': 'Email',
                '_name': 'Email Address',
                '_description': 'The contact email address.'
            },
            'reply_email': {
                '_short': 'Reply Email',
                '_name': 'Reply Email Address',
                '_description': 'The contact reply email address.'
            },
            'updated': {
                '_short': 'Updated',
                '_name': 'Updated Timestamp',
                '_description': 'The date the contact was updated in ISO 8601 '
                                'format.'
            }
        }
    }
}
