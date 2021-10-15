# -*- coding: utf-8 -*-
"""Tests of Beautiful Soup as a whole."""

from pdb import set_trace
import logging
import os
import unittest
import sys
import tempfile

from bs4 import (
    BeautifulSoup,
    BeautifulStoneSoup,
    GuessedAtParserWarning,
    MarkupResemblesLocatorWarning,
)
from bs4.builder import (
    TreeBuilder,
    ParserRejectedMarkup,
)
from bs4.element import (
    CharsetMetaAttributeValue,
    Comment,
    ContentMetaAttributeValue,
    SoupStrainer,
    NamespacedAttribute,
    Tag,
    NavigableString,
    )

import bs4.dammit
from bs4.dammit import (
    EntitySubstitution,
    UnicodeDammit,
)
from bs4.testing import (
    default_builder,
    SoupTest,
    skipIf,
)
import warnings

try:
    from bs4.builder import LXMLTreeBuilder, LXMLTreeBuilderForXML
    LXML_PRESENT = True
except ImportError as e:
    LXML_PRESENT = False

PYTHON_3_PRE_3_2 = (sys.version_info[0] == 3 and sys.version_info < (3,2))

class TestConstructor(SoupTest):

    def test_short_unicode_input(self):
        data = "<h1>éé</h1>"
        soup = self.soup(data)
        self.assertEqual("éé", soup.h1.string)

    def test_embedded_null(self):
        data = "<h1>foo\0bar</h1>"
        soup = self.soup(data)
        self.assertEqual("foo\0bar", soup.h1.string)

    def test_exclude_encodings(self):
        utf8_data = "Räksmörgås".encode("utf-8")
        soup = self.soup(utf8_data, exclude_encodings=["utf-8"])
        self.assertEqual("windows-1252", soup.original_encoding)

    def test_custom_builder_class(self):
        # Verify that you can pass in a custom Builder class and
        # it'll be instantiated with the appropriate keyword arguments.
        class Mock(object):
            def __init__(self, **kwargs):
                self.called_with = kwargs
                self.is_xml = True
                self.store_line_numbers = False
                self.cdata_list_attributes = []
                self.preserve_whitespace_tags = []
                self.string_containers = {}
            def initialize_soup(self, soup):
                pass
            def feed(self, markup):
                self.fed = markup
            def reset(self):
                pass
            def ignore(self, ignore):
                pass
            set_up_substitutions = can_be_empty_element = ignore
            def prepare_markup(self, *args, **kwargs):
                yield "prepared markup", "original encoding", "declared encoding", "contains replacement characters"
                
        kwargs = dict(
            var="value",
            # This is a deprecated BS3-era keyword argument, which
            # will be stripped out.
            convertEntities=True,
        )
        with warnings.catch_warnings(record=True):
            soup = BeautifulSoup('', builder=Mock, **kwargs)
        assert isinstance(soup.builder, Mock)
        self.assertEqual(dict(var="value"), soup.builder.called_with)
        self.assertEqual("prepared markup", soup.builder.fed)
        
        # You can also instantiate the TreeBuilder yourself. In this
        # case, that specific object is used and any keyword arguments
        # to the BeautifulSoup constructor are ignored.
        builder = Mock(**kwargs)
        with warnings.catch_warnings(record=True) as w:
            soup = BeautifulSoup(
                '', builder=builder, ignored_value=True,
            )
        msg = str(w[0].message)
        assert msg.startswith("Keyword arguments to the BeautifulSoup constructor will be ignored.")
        self.assertEqual(builder, soup.builder)
        self.assertEqual(kwargs, builder.called_with)

    def test_parser_markup_rejection(self):
        # If markup is completely rejected by the parser, an
        # explanatory ParserRejectedMarkup exception is raised.
        class Mock(TreeBuilder):
            def feed(self, *args, **kwargs):
                raise ParserRejectedMarkup("Nope.")

        def prepare_markup(self, *args, **kwargs):
            # We're going to try two different ways of preparing this markup,
            # but feed() will reject both of them.
            yield markup, None, None, False
            yield markup, None, None, False
            
        import re
        self.assertRaisesRegex(
            ParserRejectedMarkup,
            "The markup you provided was rejected by the parser. Trying a different parser or a different encoding may help.",
            BeautifulSoup, '', builder=Mock,
        )
        
    def test_cdata_list_attributes(self):
        # Most attribute values are represented as scalars, but the
        # HTML standard says that some attributes, like 'class' have
        # space-separated lists as values.
        markup = '<a id=" an id " class=" a class "></a>'
        soup = self.soup(markup)

        # Note that the spaces are stripped for 'class' but not for 'id'.
        a = soup.a
        self.assertEqual(" an id ", a['id'])
        self.assertEqual(["a", "class"], a['class'])

        # TreeBuilder takes an argument called 'mutli_valued_attributes'  which lets
        # you customize or disable this. As always, you can customize the TreeBuilder
        # by passing in a keyword argument to the BeautifulSoup constructor.
        soup = self.soup(markup, builder=default_builder, multi_valued_attributes=None)
        self.assertEqual(" a class ", soup.a['class'])

        # Here are two ways of saying that `id` is a multi-valued
        # attribute in this context, but 'class' is not.
        for switcheroo in ({'*': 'id'}, {'a': 'id'}):
            with warnings.catch_warnings(record=True) as w:
                # This will create a warning about not explicitly
                # specifying a parser, but we'll ignore it.
                soup = self.soup(markup, builder=None, multi_valued_attributes=switcheroo)
            a = soup.a
            self.assertEqual(["an", "id"], a['id'])
            self.assertEqual(" a class ", a['class'])

    def test_replacement_classes(self):
        # Test the ability to pass in replacements for element classes
        # which will be used when building the tree.
        class TagPlus(Tag):
            pass

        class StringPlus(NavigableString):
            pass

        class CommentPlus(Comment):
            pass
        
        soup = self.soup(
            "<a><b>foo</b>bar</a><!--whee-->",
            element_classes = {
                Tag: TagPlus,
                NavigableString: StringPlus,
                Comment: CommentPlus,
            }
        )

        # The tree was built with TagPlus, StringPlus, and CommentPlus objects,
        # rather than Tag, String, and Comment objects.
        assert all(
            isinstance(x, (TagPlus, StringPlus, CommentPlus))
            for x in soup.recursiveChildGenerator()
        )

    def test_alternate_string_containers(self):
        # Test the ability to customize the string containers for
        # different types of tags.
        class PString(NavigableString):
            pass

        class BString(NavigableString):
            pass

        soup = self.soup(
            "<div>Hello.<p>Here is <b>some <i>bolded</i></b> text",
            string_containers = {
                'b': BString,
                'p': PString,
            }
        )

        # The string before the <p> tag is a regular NavigableString.
        assert isinstance(soup.div.contents[0], NavigableString)
        
        # The string inside the <p> tag, but not inside the <i> tag,
        # is a PString.
        assert isinstance(soup.p.contents[0], PString)

        # Every string inside the <b> tag is a BString, even the one that
        # was also inside an <i> tag.
        for s in soup.b.strings:
            assert isinstance(s, BString)

        # Now that parsing was complete, the string_container_stack
        # (where this information was kept) has been cleared out.
        self.assertEqual([], soup.string_container_stack)


class TestWarnings(SoupTest):

    def _assert_warning(self, warnings, cls):
        for w in warnings:
            if isinstance(w.message, cls):
                return w
        raise Exception("%s warning not found in %r" % cls, warnings)
    
    def _assert_no_parser_specified(self, w):
        warning = self._assert_warning(w, GuessedAtParserWarning)
        message = str(warning.message)
        self.assertTrue(
            message.startswith(BeautifulSoup.NO_PARSER_SPECIFIED_WARNING[:60])
        )

    def test_warning_if_no_parser_specified(self):
        with warnings.catch_warnings(record=True) as w:
            soup = BeautifulSoup("<a><b></b></a>")
        self._assert_no_parser_specified(w)

    def test_warning_if_parser_specified_too_vague(self):
        with warnings.catch_warnings(record=True) as w:
            soup = BeautifulSoup("<a><b></b></a>", "html")
        self._assert_no_parser_specified(w)

    def test_no_warning_if_explicit_parser_specified(self):
        with warnings.catch_warnings(record=True) as w:
            soup = BeautifulSoup("<a><b></b></a>", "html.parser")
        self.assertEqual([], w)

    def test_parseOnlyThese_renamed_to_parse_only(self):
        with warnings.catch_warnings(record=True) as w:
            soup = self.soup("<a><b></b></a>", parseOnlyThese=SoupStrainer("b"))
        msg = str(w[0].message)
        self.assertTrue("parseOnlyThese" in msg)
        self.assertTrue("parse_only" in msg)
        self.assertEqual(b"<b></b>", soup.encode())

    def test_fromEncoding_renamed_to_from_encoding(self):
        with warnings.catch_warnings(record=True) as w:
            utf8 = b"\xc3\xa9"
            soup = self.soup(utf8, fromEncoding="utf8")
        msg = str(w[0].message)
        self.assertTrue("fromEncoding" in msg)
        self.assertTrue("from_encoding" in msg)
        self.assertEqual("utf8", soup.original_encoding)

    def test_unrecognized_keyword_argument(self):
        self.assertRaises(
            TypeError, self.soup, "<a>", no_such_argument=True)

    def test_disk_file_warning(self):
        filehandle = tempfile.NamedTemporaryFile()
        filename = filehandle.name
        try:
            with warnings.catch_warnings(record=True) as w:
                soup = self.soup(filename)
            warning = self._assert_warning(w, MarkupResemblesLocatorWarning)
            self.assertTrue("looks like a filename" in str(warning.message))
        finally:
            filehandle.close()

        # The file no longer exists, so Beautiful Soup will no longer issue the warning.
        with warnings.catch_warnings(record=True) as w:
            soup = self.soup(filename)
        self.assertEqual([], w)

    def test_directory_warning(self):
        try:
            filename = tempfile.mkdtemp()
            with warnings.catch_warnings(record=True) as w:
                soup = self.soup(filename)
            warning = self._assert_warning(w, MarkupResemblesLocatorWarning)
            self.assertTrue("looks like a directory" in str(warning.message))
        finally:
            os.rmdir(filename)

        # The directory no longer exists, so Beautiful Soup will no longer issue the warning.
        with warnings.catch_warnings(record=True) as w:
            soup = self.soup(filename)
        self.assertEqual([], w)
        
    def test_url_warning_with_bytes_url(self):
        with warnings.catch_warnings(record=True) as warning_list:
            soup = self.soup(b"http://www.crummybytes.com/")
        warning = self._assert_warning(
            warning_list, MarkupResemblesLocatorWarning
        )
        self.assertTrue("looks like a URL" in str(warning.message))

    def test_url_warning_with_unicode_url(self):
        with warnings.catch_warnings(record=True) as warning_list:
            # note - this url must differ from the bytes one otherwise
            # python's warnings system swallows the second warning
            soup = self.soup("http://www.crummyunicode.com/")
        warning = self._assert_warning(
            warning_list, MarkupResemblesLocatorWarning
        )
        self.assertTrue("looks like a URL" in str(warning.message))

    def test_url_warning_with_bytes_and_space(self):
        # Here the markup contains something besides a URL, so no warning
        # is issued.
        with warnings.catch_warnings(record=True) as warning_list:
            soup = self.soup(b"http://www.crummybytes.com/ is great")
        self.assertFalse(any("looks like a URL" in str(w.message) 
            for w in warning_list))

    def test_url_warning_with_unicode_and_space(self):
        with warnings.catch_warnings(record=True) as warning_list:
            soup = self.soup("http://www.crummyuncode.com/ is great")
        self.assertFalse(any("looks like a URL" in str(w.message) 
            for w in warning_list))


class TestSelectiveParsing(SoupTest):

    def test_parse_with_soupstrainer(self):
        markup = "No<b>Yes</b><a>No<b>Yes <c>Yes</c></b>"
        strainer = SoupStrainer("b")
        soup = self.soup(markup, parse_only=strainer)
        self.assertEqual(soup.encode(), b"<b>Yes</b><b>Yes <c>Yes</c></b>")


class TestEntitySubstitution(unittest.TestCase):
    """Standalone tests of the EntitySubstitution class."""
    def setUp(self):
        self.sub = EntitySubstitution

    def test_simple_html_substitution(self):
        # Unicode characters corresponding to named HTML entites
        # are substituted, and no others.
        s = "foo\u2200\N{SNOWMAN}\u00f5bar"
        self.assertEqual(self.sub.substitute_html(s),
                          "foo&forall;\N{SNOWMAN}&otilde;bar")

    def test_smart_quote_substitution(self):
        # MS smart quotes are a common source of frustration, so we
        # give them a special test.
        quotes = b"\x91\x92foo\x93\x94"
        dammit = UnicodeDammit(quotes)
        self.assertEqual(self.sub.substitute_html(dammit.markup),
                          "&lsquo;&rsquo;foo&ldquo;&rdquo;")

    def test_html5_entity(self):
        # Some HTML5 entities correspond to single- or multi-character
        # Unicode sequences.

        for entity, u in (
            # A few spot checks of our ability to recognize
            # special character sequences and convert them
            # to named entities.
            ('&models;', '\u22a7'),
            ('&Nfr;', '\U0001d511'),
            ('&ngeqq;', '\u2267\u0338'),
            ('&not;', '\xac'),
            ('&Not;', '\u2aec'),
                
            # We _could_ convert | to &verbarr;, but we don't, because
            # | is an ASCII character.
            ('|' '|'),

            # Similarly for the fj ligature, which we could convert to
            # &fjlig;, but we don't.
            ("fj", "fj"),

            # We do convert _these_ ASCII characters to HTML entities,
            # because that's required to generate valid HTML.
            ('&gt;', '>'),
            ('&lt;', '<'),
            ('&amp;', '&'),
        ):
            template = '3 %s 4'
            raw = template % u
            with_entities = template % entity
            self.assertEqual(self.sub.substitute_html(raw), with_entities)
            
    def test_html5_entity_with_variation_selector(self):
        # Some HTML5 entities correspond either to a single-character
        # Unicode sequence _or_ to the same character plus U+FE00,
        # VARIATION SELECTOR 1. We can handle this.
        data = "fjords \u2294 penguins"
        markup = "fjords &sqcup; penguins"
        self.assertEqual(self.sub.substitute_html(data), markup)

        data = "fjords \u2294\ufe00 penguins"
        markup = "fjords &sqcups; penguins"
        self.assertEqual(self.sub.substitute_html(data), markup)
        
    def test_xml_converstion_includes_no_quotes_if_make_quoted_attribute_is_false(self):
        s = 'Welcome to "my bar"'
        self.assertEqual(self.sub.substitute_xml(s, False), s)

    def test_xml_attribute_quoting_normally_uses_double_quotes(self):
        self.assertEqual(self.sub.substitute_xml("Welcome", True),
                          '"Welcome"')
        self.assertEqual(self.sub.substitute_xml("Bob's Bar", True),
                          '"Bob\'s Bar"')

    def test_xml_attribute_quoting_uses_single_quotes_when_value_contains_double_quotes(self):
        s = 'Welcome to "my bar"'
        self.assertEqual(self.sub.substitute_xml(s, True),
                          "'Welcome to \"my bar\"'")

    def test_xml_attribute_quoting_escapes_single_quotes_when_value_contains_both_single_and_double_quotes(self):
        s = 'Welcome to "Bob\'s Bar"'
        self.assertEqual(
            self.sub.substitute_xml(s, True),
            '"Welcome to &quot;Bob\'s Bar&quot;"')

    def test_xml_quotes_arent_escaped_when_value_is_not_being_quoted(self):
        quoted = 'Welcome to "Bob\'s Bar"'
        self.assertEqual(self.sub.substitute_xml(quoted), quoted)

    def test_xml_quoting_handles_angle_brackets(self):
        self.assertEqual(
            self.sub.substitute_xml("foo<bar>"),
            "foo&lt;bar&gt;")

    def test_xml_quoting_handles_ampersands(self):
        self.assertEqual(self.sub.substitute_xml("AT&T"), "AT&amp;T")

    def test_xml_quoting_including_ampersands_when_they_are_part_of_an_entity(self):
        self.assertEqual(
            self.sub.substitute_xml("&Aacute;T&T"),
            "&amp;Aacute;T&amp;T")

    def test_xml_quoting_ignoring_ampersands_when_they_are_part_of_an_entity(self):
        self.assertEqual(
            self.sub.substitute_xml_containing_entities("&Aacute;T&T"),
            "&Aacute;T&amp;T")
       
    def test_quotes_not_html_substituted(self):
        """There's no need to do this except inside attribute values."""
        text = 'Bob\'s "bar"'
        self.assertEqual(self.sub.substitute_html(text), text)


class TestEncodingConversion(SoupTest):
    # Test Beautiful Soup's ability to decode and encode from various
    # encodings.

    def setUp(self):
        super(TestEncodingConversion, self).setUp()
        self.unicode_data = '<html><head><meta charset="utf-8"/></head><body><foo>Sacr\N{LATIN SMALL LETTER E WITH ACUTE} bleu!</foo></body></html>'
        self.utf8_data = self.unicode_data.encode("utf-8")
        # Just so you know what it looks like.
        self.assertEqual(
            self.utf8_data,
            b'<html><head><meta charset="utf-8"/></head><body><foo>Sacr\xc3\xa9 bleu!</foo></body></html>')

    def test_ascii_in_unicode_out(self):
        # ASCII input is converted to Unicode. The original_encoding
        # attribute is set to 'utf-8', a superset of ASCII.
        chardet = bs4.dammit.chardet_dammit
        logging.disable(logging.WARNING)
        try:
            def noop(str):
                return None
            # Disable chardet, which will realize that the ASCII is ASCII.
            bs4.dammit.chardet_dammit = noop
            ascii = b"<foo>a</foo>"
            soup_from_ascii = self.soup(ascii)
            unicode_output = soup_from_ascii.decode()
            self.assertTrue(isinstance(unicode_output, str))
            self.assertEqual(unicode_output, self.document_for(ascii.decode()))
            self.assertEqual(soup_from_ascii.original_encoding.lower(), "utf-8")
        finally:
            logging.disable(logging.NOTSET)
            bs4.dammit.chardet_dammit = chardet

    def test_unicode_in_unicode_out(self):
        # Unicode input is left alone. The original_encoding attribute
        # is not set.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.decode(), self.unicode_data)
        self.assertEqual(soup_from_unicode.foo.string, 'Sacr\xe9 bleu!')
        self.assertEqual(soup_from_unicode.original_encoding, None)

    def test_utf8_in_unicode_out(self):
        # UTF-8 input is converted to Unicode. The original_encoding
        # attribute is set.
        soup_from_utf8 = self.soup(self.utf8_data)
        self.assertEqual(soup_from_utf8.decode(), self.unicode_data)
        self.assertEqual(soup_from_utf8.foo.string, 'Sacr\xe9 bleu!')

    def test_utf8_out(self):
        # The internal data structures can be encoded as UTF-8.
        soup_from_unicode = self.soup(self.unicode_data)
        self.assertEqual(soup_from_unicode.encode('utf-8'), self.utf8_data)

    @skipIf(
        PYTHON_3_PRE_3_2,
        "Bad HTMLParser detected; skipping test of non-ASCII characters in attribute name.")
    def test_attribute_name_containing_unicode_characters(self):
        markup = '<div><a \N{SNOWMAN}="snowman"></a></div>'
        self.assertEqual(self.soup(markup).div.encode("utf8"), markup.encode("utf8"))


class TestNamedspacedAttribute(SoupTest):

    def test_name_may_be_none_or_missing(self):
        a = NamespacedAttribute("xmlns", None)
        self.assertEqual(a, "xmlns")

        a = NamespacedAttribute("xmlns", "")
        self.assertEqual(a, "xmlns")

        a = NamespacedAttribute("xmlns")
        self.assertEqual(a, "xmlns")
        
    def test_namespace_may_be_none_or_missing(self):
        a = NamespacedAttribute(None, "tag")
        self.assertEqual(a, "tag")
        
        a = NamespacedAttribute("", "tag")
        self.assertEqual(a, "tag")
        
    def test_attribute_is_equivalent_to_colon_separated_string(self):
        a = NamespacedAttribute("a", "b")
        self.assertEqual("a:b", a)

    def test_attributes_are_equivalent_if_prefix_and_name_identical(self):
        a = NamespacedAttribute("a", "b", "c")
        b = NamespacedAttribute("a", "b", "c")
        self.assertEqual(a, b)

        # The actual namespace is not considered.
        c = NamespacedAttribute("a", "b", None)
        self.assertEqual(a, c)

        # But name and prefix are important.
        d = NamespacedAttribute("a", "z", "c")
        self.assertNotEqual(a, d)

        e = NamespacedAttribute("z", "b", "c")
        self.assertNotEqual(a, e)


class TestAttributeValueWithCharsetSubstitution(unittest.TestCase):

    def test_content_meta_attribute_value(self):
        value = CharsetMetaAttributeValue("euc-jp")
        self.assertEqual("euc-jp", value)
        self.assertEqual("euc-jp", value.original_value)
        self.assertEqual("utf8", value.encode("utf8"))


    def test_content_meta_attribute_value(self):
        value = ContentMetaAttributeValue("text/html; charset=euc-jp")
        self.assertEqual("text/html; charset=euc-jp", value)
        self.assertEqual("text/html; charset=euc-jp", value.original_value)
        self.assertEqual("text/html; charset=utf8", value.encode("utf8"))
