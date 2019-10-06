# This file is part of the musicbrainzngs library
# Copyright (C) Alastair Porter, Adrian Sampson, and others
# This file is distributed under a BSD-2-Clause type license.
# See the COPYING file for more information.

import re
import xml.etree.ElementTree as ET
import logging

from . import util


def fixtag(tag, namespaces):
    # given a decorated tag (of the form {uri}tag), return prefixed
    # tag and namespace declaration, if any
    if isinstance(tag, ET.QName):
        tag = tag.text
    namespace_uri, tag = tag[1:].split("}", 1)
    prefix = namespaces.get(namespace_uri)
    if prefix is None:
        prefix = "ns%d" % len(namespaces)
        namespaces[namespace_uri] = prefix
        if prefix == "xml":
            xmlns = None
        else:
            xmlns = ("xmlns:%s" % prefix, namespace_uri)
    else:
        xmlns = None
    return "%s:%s" % (prefix, tag), xmlns


NS_MAP = {"http://musicbrainz.org/ns/mmd-2.0#": "ws2",
          "http://musicbrainz.org/ns/ext#-2.0": "ext"}
_log = logging.getLogger("musicbrainzngs")

def get_error_message(error):
    """ Given an error XML message from the webservice containing
    <error><text>x</text><text>y</text></error>, return a list
    of [x, y]"""
    try:
        tree = util.bytes_to_elementtree(error)
        root = tree.getroot()
        errors = []
        if root.tag == "error":
            for ch in root:
                if ch.tag == "text":
                    errors.append(ch.text)
        return errors
    except ET.ParseError:
        return None

def make_artist_credit(artists):
    names = []
    for artist in artists:
        if isinstance(artist, dict):
            if "name" in artist:
                names.append(artist.get("name", ""))
            else:
                names.append(artist.get("artist", {}).get("name", ""))
        else:
                names.append(artist)
    return "".join(names)

def parse_elements(valid_els, inner_els, element):
    """ Extract single level subelements from an element.
        For example, given the element:
        <element>
            <subelement>Text</subelement>
        </element>
        and a list valid_els that contains "subelement",
        return a dict {'subelement': 'Text'}

        Delegate the parsing of multi-level subelements to another function.
        For example, given the element:
        <element>
            <subelement>
                <a>Foo</a><b>Bar</b>
            </subelement>
        </element>
        and a dictionary {'subelement': parse_subelement},
        call parse_subelement(<subelement>) and
        return a dict {'subelement': <result>}
        if parse_subelement returns a tuple of the form
        (True, {'subelement-key': <result>})
        then merge the second element of the tuple into the
        result (which may have a key other than 'subelement' or
        more than 1 key)
    """
    result = {}
    for sub in element:
        t = fixtag(sub.tag, NS_MAP)[0]
        if ":" in t:
            t = t.split(":")[1]
        if t in valid_els:
            result[t] = sub.text or ""
        elif t in inner_els.keys():
            inner_result = inner_els[t](sub)
            if isinstance(inner_result, tuple) and inner_result[0]:
                result.update(inner_result[1])
            else:
                result[t] = inner_result
            # add counts for lists when available
            m = re.match(r'([a-z0-9-]+)-list', t)
            if m and "count" in sub.attrib:
                result["%s-count" % m.group(1)] = int(sub.attrib["count"])
        else:
            _log.info("in <%s>, uncaught <%s>",
                      fixtag(element.tag, NS_MAP)[0], t)
    return result

def parse_attributes(attributes, element):
    """ Extract attributes from an element.
        For example, given the element:
        <element type="Group" />
        and a list attributes that contains "type",
        return a dict {'type': 'Group'}
    """
    result = {}
    for attr in element.attrib:
        if "{" in attr:
            a = fixtag(attr, NS_MAP)[0]
        else:
            a = attr
        if a in attributes:
            result[a] = element.attrib[attr]
        else:
            _log.info("in <%s>, uncaught attribute %s", fixtag(element.tag, NS_MAP)[0], attr)

    return result

def parse_message(message):
    tree = util.bytes_to_elementtree(message)
    root = tree.getroot()
    result = {}
    valid_elements = {"area": parse_area,
                      "artist": parse_artist,
                      "instrument": parse_instrument,
                      "label": parse_label,
                      "place": parse_place,
                      "event": parse_event,
                      "release": parse_release,
                      "release-group": parse_release_group,
                      "series": parse_series,
                      "recording": parse_recording,
                      "work": parse_work,
                      "url": parse_url,

                      "disc": parse_disc,
                      "cdstub": parse_cdstub,
                      "isrc": parse_isrc,

                      "annotation-list": parse_annotation_list,
                      "area-list": parse_area_list,
                      "artist-list": parse_artist_list,
                      "label-list": parse_label_list,
                      "place-list": parse_place_list,
                      "event-list": parse_event_list,
                      "instrument-list": parse_instrument_list,
                      "release-list": parse_release_list,
                      "release-group-list": parse_release_group_list,
                      "series-list": parse_series_list,
                      "recording-list": parse_recording_list,
                      "work-list": parse_work_list,
                      "url-list": parse_url_list,

                      "collection-list": parse_collection_list,
                      "collection": parse_collection,

                      "message": parse_response_message
                      }
    result.update(parse_elements([], valid_elements, root))
    return result

def parse_response_message(message):
    return parse_elements(["text"], {}, message)

def parse_collection_list(cl):
    return [parse_collection(c) for c in cl]

def parse_collection(collection):
    result = {}
    attribs = ["id", "type", "entity-type"]
    elements = ["name", "editor"]
    inner_els = {"release-list": parse_release_list,
                 "artist-list": parse_artist_list,
                 "event-list": parse_event_list,
                 "place-list": parse_place_list,
                 "recording-list": parse_recording_list,
                 "work-list": parse_work_list}
    result.update(parse_attributes(attribs, collection))
    result.update(parse_elements(elements, inner_els, collection))

    return result

def parse_annotation_list(al):
    return [parse_annotation(a) for a in al]

def parse_annotation(annotation):
    result = {}
    attribs = ["type", "ext:score"]
    elements = ["entity", "name", "text"]
    result.update(parse_attributes(attribs, annotation))
    result.update(parse_elements(elements, {}, annotation))
    return result

def parse_lifespan(lifespan):
    parts = parse_elements(["begin", "end", "ended"], {}, lifespan)

    return parts

def parse_area_list(al):
    return [parse_area(a) for a in al]

def parse_area(area):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["name", "sort-name", "disambiguation"]
    inner_els = {"life-span": parse_lifespan,
                 "alias-list": parse_alias_list,
                 "relation-list": parse_relation_list,
                 "annotation": parse_annotation,
                 "iso-3166-1-code-list": parse_element_list,
                 "iso-3166-2-code-list": parse_element_list,
                 "iso-3166-3-code-list": parse_element_list}

    result.update(parse_attributes(attribs, area))
    result.update(parse_elements(elements, inner_els, area))

    return result

def parse_artist_list(al):
    return [parse_artist(a) for a in al]

def parse_artist(artist):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["name", "sort-name", "country", "user-rating",
                "disambiguation", "gender", "ipi"]
    inner_els = {"area": parse_area,
                 "begin-area": parse_area,
                 "end-area": parse_area,
                 "life-span": parse_lifespan,
                 "recording-list": parse_recording_list,
                 "relation-list": parse_relation_list,
                 "release-list": parse_release_list,
                 "release-group-list": parse_release_group_list,
                 "work-list": parse_work_list,
                 "tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "rating": parse_rating,
                 "ipi-list": parse_element_list,
                 "isni-list": parse_element_list,
                 "alias-list": parse_alias_list,
                 "annotation": parse_annotation}

    result.update(parse_attributes(attribs, artist))
    result.update(parse_elements(elements, inner_els, artist))

    return result

def parse_coordinates(c):
    return parse_elements(['latitude', 'longitude'], {}, c)

def parse_place_list(pl):
    return [parse_place(p) for p in pl]

def parse_place(place):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["name", "address",
                "ipi", "disambiguation"]
    inner_els = {"area": parse_area,
                 "coordinates": parse_coordinates,
                 "life-span": parse_lifespan,
                 "tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "alias-list": parse_alias_list,
                 "relation-list": parse_relation_list,
                 "annotation": parse_annotation}

    result.update(parse_attributes(attribs, place))
    result.update(parse_elements(elements, inner_els, place))

    return result

def parse_event_list(el):
    return [parse_event(e) for e in el]

def parse_event(event):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["name", "time", "setlist", "cancelled", "disambiguation", "user-rating"]
    inner_els = {"life-span": parse_lifespan,
                 "relation-list": parse_relation_list,
                 "alias-list": parse_alias_list,
                 "tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "rating": parse_rating}

    result.update(parse_attributes(attribs, event))
    result.update(parse_elements(elements, inner_els, event))

    return result

def parse_instrument(instrument):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["name", "description", "disambiguation"]
    inner_els = {"relation-list": parse_relation_list,
                 "tag-list": parse_tag_list,
                 "alias-list": parse_alias_list,
                 "annotation": parse_annotation}
    result.update(parse_attributes(attribs, instrument))
    result.update(parse_elements(elements, inner_els, instrument))

    return result

def parse_label_list(ll):
    return [parse_label(l) for l in ll]

def parse_label(label):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["name", "sort-name", "country", "label-code", "user-rating",
                "ipi", "disambiguation"]
    inner_els = {"area": parse_area,
                 "life-span": parse_lifespan,
                 "release-list": parse_release_list,
                 "tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "rating": parse_rating,
                 "ipi-list": parse_element_list,
                 "alias-list": parse_alias_list,
                 "relation-list": parse_relation_list,
                 "annotation": parse_annotation}

    result.update(parse_attributes(attribs, label))
    result.update(parse_elements(elements, inner_els, label))

    return result

def parse_relation_target(tgt):
    attributes = parse_attributes(['id'], tgt)
    if 'id' in attributes:
        return (True, {'target-id': attributes['id']})
    else:
        return (True, {'target-id': tgt.text})

def parse_relation_list(rl):
    attribs = ["target-type"]
    ttype = parse_attributes(attribs, rl)
    key = "%s-relation-list" % ttype["target-type"]
    return (True, {key: [parse_relation(r) for r in rl]})

def parse_relation(relation):
    result = {}
    attribs = ["type", "type-id"]
    elements = ["target", "direction", "begin", "end", "ended", "ordering-key"]
    inner_els = {"area": parse_area,
                 "artist": parse_artist,
                 "instrument": parse_instrument,
                 "label": parse_label,
                 "place": parse_place,
                 "event": parse_event,
                 "recording": parse_recording,
                 "release": parse_release,
                 "release-group": parse_release_group,
                 "series": parse_series,
                 "attribute-list": parse_element_list,
                 "work": parse_work,
                 "target": parse_relation_target
                }
    result.update(parse_attributes(attribs, relation))
    result.update(parse_elements(elements, inner_els, relation))
    # We parse attribute-list again to get attributes that have both
    # text and attribute values
    result.update(parse_elements(['target-credit'], {"attribute-list": parse_relation_attribute_list}, relation))

    return result

def parse_relation_attribute_list(attributelist):
    ret = []
    for attribute in attributelist:
        ret.append(parse_relation_attribute_element(attribute))
    return (True, {"attributes": ret})

def parse_relation_attribute_element(element):
    # Parses an attribute into a dictionary containing an element
    # {"attribute": <text value>} and also an additional element
    # containing any xml attributes.
    # e.g <attribute value="BuxWV 1">number</attribute>
    # -> {"attribute": "number", "value": "BuxWV 1"}
    result = {}
    for attr in element.attrib:
        if "{" in attr:
            a = fixtag(attr, NS_MAP)[0]
        else:
            a = attr
        result[a] = element.attrib[attr]
    result["attribute"] = element.text
    return result

def parse_release(release):
    result = {}
    attribs = ["id", "ext:score"]
    elements = ["title", "status", "disambiguation", "quality", "country",
                "barcode", "date", "packaging", "asin"]
    inner_els = {"text-representation": parse_text_representation,
                 "artist-credit": parse_artist_credit,
                 "label-info-list": parse_label_info_list,
                 "medium-list": parse_medium_list,
                 "release-group": parse_release_group,
                 "tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "relation-list": parse_relation_list,
                 "annotation": parse_annotation,
                 "cover-art-archive": parse_caa,
                 "release-event-list": parse_release_event_list}

    result.update(parse_attributes(attribs, release))
    result.update(parse_elements(elements, inner_els, release))
    if "artist-credit" in result:
        result["artist-credit-phrase"] = make_artist_credit(
                                                        result["artist-credit"])

    return result

def parse_medium_list(ml):
    """medium-list results from search have an additional
    <track-count> element containing the number of tracks
    over all mediums. Optionally add this"""
    medium_list = []
    track_count = None
    for m in ml:
        tag = fixtag(m.tag, NS_MAP)[0]
        if tag == "ws2:medium":
            medium_list.append(parse_medium(m))
        elif tag == "ws2:track-count":
            track_count = int(m.text)
    ret = {"medium-list": medium_list}
    if track_count is not None:
        ret["medium-track-count"] = track_count

    return (True, ret)

def parse_release_event_list(rel):
    return [parse_release_event(re) for re in rel]

def parse_release_event(event):
    result = {}
    elements = ["date"]
    inner_els = {"area": parse_area}

    result.update(parse_elements(elements, inner_els, event))
    return result

def parse_medium(medium):
    result = {}
    elements = ["position", "format", "title"]
    inner_els = {"disc-list": parse_disc_list,
                 "pregap": parse_track,
                 "track-list": parse_track_list,
                 "data-track-list": parse_track_list}

    result.update(parse_elements(elements, inner_els, medium))
    return result

def parse_disc_list(dl):
    return [parse_disc(d) for d in dl]

def parse_text_representation(textr):
    return parse_elements(["language", "script"], {}, textr)

def parse_release_group(rg):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["title", "user-rating", "first-release-date", "primary-type",
                "disambiguation"]
    inner_els = {"artist-credit": parse_artist_credit,
                 "release-list": parse_release_list,
                 "tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "secondary-type-list": parse_element_list,
                 "relation-list": parse_relation_list,
                 "rating": parse_rating,
                 "annotation": parse_annotation}

    result.update(parse_attributes(attribs, rg))
    result.update(parse_elements(elements, inner_els, rg))
    if "artist-credit" in result:
        result["artist-credit-phrase"] = make_artist_credit(result["artist-credit"])

    return result

def parse_recording(recording):
    result = {}
    attribs = ["id", "ext:score"]
    elements = ["title", "length", "user-rating", "disambiguation", "video"]
    inner_els = {"artist-credit": parse_artist_credit,
                 "release-list": parse_release_list,
                 "tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "rating": parse_rating,
                 "isrc-list": parse_external_id_list,
                 "relation-list": parse_relation_list,
                 "annotation": parse_annotation}

    result.update(parse_attributes(attribs, recording))
    result.update(parse_elements(elements, inner_els, recording))
    if "artist-credit" in result:
        result["artist-credit-phrase"] = make_artist_credit(result["artist-credit"])

    return result

def parse_series_list(sl):
    return [parse_series(s) for s in sl]

def parse_series(series):
    result = {}
    attribs = ["id", "type", "ext:score"]
    elements = ["name", "disambiguation"]
    inner_els = {"alias-list": parse_alias_list,
                 "relation-list": parse_relation_list,
                 "annotation": parse_annotation}

    result.update(parse_attributes(attribs, series))
    result.update(parse_elements(elements, inner_els, series))

    return result

def parse_external_id_list(pl):
    return [parse_attributes(["id"], p)["id"] for p in pl]

def parse_element_list(el):
    return [e.text for e in el]

def parse_work_list(wl):
    return [parse_work(w) for w in wl]

def parse_work(work):
    result = {}
    attribs = ["id", "ext:score", "type"]
    elements = ["title", "user-rating", "language", "iswc", "disambiguation"]
    inner_els = {"tag-list": parse_tag_list,
                 "user-tag-list": parse_tag_list,
                 "rating": parse_rating,
                 "alias-list": parse_alias_list,
                 "iswc-list": parse_element_list,
                 "relation-list": parse_relation_list,
                 "annotation": parse_response_message,
                 "attribute-list": parse_work_attribute_list
    }

    result.update(parse_attributes(attribs, work))
    result.update(parse_elements(elements, inner_els, work))

    return result

def parse_work_attribute_list(wal):
    return [parse_work_attribute(wa) for wa in wal]

def parse_work_attribute(wa):
    attribs = ["type"]
    typeinfo = parse_attributes(attribs, wa)
    result = {}
    if typeinfo:
        result = {"attribute": typeinfo["type"],
                  "value": wa.text}

    return result


def parse_url_list(ul):
    return [parse_url(u) for u in ul]

def parse_url(url):
    result = {}
    attribs = ["id"]
    elements = ["resource"]
    inner_els = {"relation-list": parse_relation_list}

    result.update(parse_attributes(attribs, url))
    result.update(parse_elements(elements, inner_els, url))

    return result

def parse_disc(disc):
    result = {}
    attribs = ["id"]
    elements = ["sectors"]
    inner_els = {"release-list": parse_release_list,
                 "offset-list": parse_offset_list
    }

    result.update(parse_attributes(attribs, disc))
    result.update(parse_elements(elements, inner_els, disc))

    return result

def parse_cdstub(cdstub):
    result = {}
    attribs = ["id"]
    elements = ["title", "artist", "barcode"]
    inner_els = {"track-list": parse_track_list}

    result.update(parse_attributes(attribs, cdstub))
    result.update(parse_elements(elements, inner_els, cdstub))

    return result

def parse_offset_list(ol):
    return [int(o.text) for o in ol]

def parse_instrument_list(rl):
    result = []
    for r in rl:
        result.append(parse_instrument(r))
    return result

def parse_release_list(rl):
    result = []
    for r in rl:
        result.append(parse_release(r))
    return result

def parse_release_group_list(rgl):
    result = []
    for rg in rgl:
        result.append(parse_release_group(rg))
    return result

def parse_isrc(isrc):
    result = {}
    attribs = ["id"]
    inner_els = {"recording-list": parse_recording_list}

    result.update(parse_attributes(attribs, isrc))
    result.update(parse_elements([], inner_els, isrc))

    return result

def parse_recording_list(recs):
    result = []
    for r in recs:
        result.append(parse_recording(r))
    return result

def parse_artist_credit(ac):
    result = []
    for namecredit in ac:
        result.append(parse_name_credit(namecredit))
        join = parse_attributes(["joinphrase"], namecredit)
        if "joinphrase" in join:
            result.append(join["joinphrase"])
    return result

def parse_name_credit(nc):
    result = {}
    elements = ["name"]
    inner_els = {"artist": parse_artist}

    result.update(parse_elements(elements, inner_els, nc))

    return result

def parse_label_info_list(lil):
    result = []

    for li in lil:
        result.append(parse_label_info(li))
    return result

def parse_label_info(li):
    result = {}
    elements = ["catalog-number"]
    inner_els = {"label": parse_label}

    result.update(parse_elements(elements, inner_els, li))
    return result

def parse_track_list(tl):
    result = []
    for t in tl:
        result.append(parse_track(t))
    return result

def parse_track(track):
    result = {}
    attribs = ["id"]
    elements = ["number", "position", "title", "length"]
    inner_els = {"recording": parse_recording,
                 "artist-credit": parse_artist_credit}

    result.update(parse_attributes(attribs, track))
    result.update(parse_elements(elements, inner_els, track))
    if "artist-credit" in result.get("recording", {}) and "artist-credit" not in result:
        result["artist-credit"] = result["recording"]["artist-credit"]
    if "artist-credit" in result:
        result["artist-credit-phrase"] = make_artist_credit(result["artist-credit"])
    # Make a length field that contains track length or recording length
    track_or_recording = None
    if "length" in result:
        track_or_recording = result["length"]
    elif result.get("recording", {}).get("length"):
        track_or_recording = result.get("recording", {}).get("length")
    if track_or_recording:
        result["track_or_recording_length"] = track_or_recording
    return result

def parse_tag_list(tl):
    return [parse_tag(t) for t in tl]

def parse_tag(tag):
    result = {}
    attribs = ["count"]
    elements = ["name"]

    result.update(parse_attributes(attribs, tag))
    result.update(parse_elements(elements, {}, tag))

    return result

def parse_rating(rating):
    result = {}
    attribs = ["votes-count"]

    result.update(parse_attributes(attribs, rating))
    result["rating"] = rating.text

    return result

def parse_alias_list(al):
    return [parse_alias(a) for a in al]

def parse_alias(alias):
    result = {}
    attribs = ["locale", "sort-name", "type", "primary",
               "begin-date", "end-date"]

    result.update(parse_attributes(attribs, alias))
    result["alias"] = alias.text

    return result

def parse_caa(caa_element):
    result = {}
    elements = ["artwork", "count", "front", "back", "darkened"]

    result.update(parse_elements(elements, {}, caa_element))
    return result


###

def make_barcode_request(release2barcode):
    NS = "http://musicbrainz.org/ns/mmd-2.0#"
    root = ET.Element("{%s}metadata" % NS)
    rel_list = ET.SubElement(root, "{%s}release-list" % NS)
    for release, barcode in release2barcode.items():
        rel_xml = ET.SubElement(rel_list, "{%s}release" % NS)
        bar_xml = ET.SubElement(rel_xml, "{%s}barcode" % NS)
        rel_xml.set("{%s}id" % NS, release)
        bar_xml.text = barcode

    return ET.tostring(root, "utf-8")

def make_tag_request(**kwargs):
    NS = "http://musicbrainz.org/ns/mmd-2.0#"
    root = ET.Element("{%s}metadata" % NS)
    for entity_type in ['artist', 'label', 'place', 'recording', 'release', 'release_group', 'work']:
        entity_tags = kwargs.pop(entity_type + '_tags', None)
        if entity_tags is not None:
            e_list = ET.SubElement(root, "{%s}%s-list" % (NS, entity_type.replace('_', '-')))
            for e, tags in entity_tags.items():
                e_xml = ET.SubElement(e_list, "{%s}%s" % (NS, entity_type.replace('_', '-')))
                e_xml.set("{%s}id" % NS, e)
                taglist = ET.SubElement(e_xml, "{%s}user-tag-list" % NS)
                for tag in tags:
                    usertag_xml = ET.SubElement(taglist, "{%s}user-tag" % NS)
                    name_xml = ET.SubElement(usertag_xml, "{%s}name" % NS)
                    name_xml.text = tag
    if kwargs.keys():
        raise TypeError("make_tag_request() got an unexpected keyword argument '%s'" % kwargs.popitem()[0])

    return ET.tostring(root, "utf-8")

def make_rating_request(**kwargs):
    NS = "http://musicbrainz.org/ns/mmd-2.0#"
    root = ET.Element("{%s}metadata" % NS)
    for entity_type in ['artist', 'label', 'recording', 'release_group', 'work']:
        entity_ratings = kwargs.pop(entity_type + '_ratings', None)
        if entity_ratings is not None:
            e_list = ET.SubElement(root, "{%s}%s-list" % (NS, entity_type.replace('_', '-')))
            for e, rating in entity_ratings.items():
                e_xml = ET.SubElement(e_list, "{%s}%s" % (NS, entity_type.replace('_', '-')))
                e_xml.set("{%s}id" % NS, e)
                rating_xml = ET.SubElement(e_xml, "{%s}user-rating" % NS)
                rating_xml.text = str(rating)
    if kwargs.keys():
        raise TypeError("make_rating_request() got an unexpected keyword argument '%s'" % kwargs.popitem()[0])

    return ET.tostring(root, "utf-8")

def make_isrc_request(recording2isrcs):
    NS = "http://musicbrainz.org/ns/mmd-2.0#"
    root = ET.Element("{%s}metadata" % NS)
    rec_list = ET.SubElement(root, "{%s}recording-list" % NS)
    for rec, isrcs in recording2isrcs.items():
        if len(isrcs) > 0:
            rec_xml = ET.SubElement(rec_list, "{%s}recording" % NS)
            rec_xml.set("{%s}id" % NS, rec)
            isrc_list_xml = ET.SubElement(rec_xml, "{%s}isrc-list" % NS)
            isrc_list_xml.set("{%s}count" % NS, str(len(isrcs)))
            for isrc in isrcs:
                isrc_xml = ET.SubElement(isrc_list_xml, "{%s}isrc" % NS)
                isrc_xml.set("{%s}id" % NS, isrc)
    return ET.tostring(root, "utf-8")
