from bs4.dammit import EntitySubstitution

class Formatter(EntitySubstitution):
    """Describes a strategy to use when outputting a parse tree to a string.

    Some parts of this strategy come from the distinction between
    HTML4, HTML5, and XML. Others are configurable by the user.
    """
    # Registries of XML and HTML formatters.
    XML_FORMATTERS = {}
    HTML_FORMATTERS = {}

    HTML = 'html'
    XML = 'xml'

    HTML_DEFAULTS = dict(
        cdata_containing_tags=set(["script", "style"]),
    )

    def _default(self, language, value, kwarg):
        if value is not None:
            return value
        if language == self.XML:
            return set()
        return self.HTML_DEFAULTS[kwarg]

    def __init__(
            self, language=None, entity_substitution=None,
            void_element_close_prefix='/', cdata_containing_tags=None,
    ):
        """

        :param void_element_close_prefix: By default, represent void
        elements as <tag/> rather than <tag>
        """
        self.language = language
        self.entity_substitution = entity_substitution
        self.void_element_close_prefix = void_element_close_prefix
        self.cdata_containing_tags = self._default(
            language, cdata_containing_tags, 'cdata_containing_tags'
        )
            
    def substitute(self, ns):
        """Process a string that needs to undergo entity substitution."""
        if not self.entity_substitution:
            return ns
        from .element import NavigableString
        if (isinstance(ns, NavigableString)
            and ns.parent is not None
            and ns.parent.name in self.cdata_containing_tags):
            # Do nothing.
            return ns
        # Substitute.
        return self.entity_substitution(ns)

    def attribute_value(self, value):
        """Process the value of an attribute."""
        return self.substitute(value)
    
    def attributes(self, tag):
        """Reorder a tag's attributes however you want."""
        return sorted(tag.attrs.items())

   
class HTMLFormatter(Formatter):
    REGISTRY = {}
    def __init__(self, *args, **kwargs):
        return super(HTMLFormatter, self).__init__(self.HTML, *args, **kwargs)

    
class XMLFormatter(Formatter):
    REGISTRY = {}
    def __init__(self, *args, **kwargs):
        return super(XMLFormatter, self).__init__(self.XML, *args, **kwargs)


# Set up aliases for the default formatters.
HTMLFormatter.REGISTRY['html'] = HTMLFormatter(
    entity_substitution=EntitySubstitution.substitute_html
)
HTMLFormatter.REGISTRY["html5"] = HTMLFormatter(
    entity_substitution=EntitySubstitution.substitute_html,
    void_element_close_prefix = None
)
HTMLFormatter.REGISTRY["minimal"] = HTMLFormatter(
    entity_substitution=EntitySubstitution.substitute_xml
)
HTMLFormatter.REGISTRY[None] = HTMLFormatter(
    entity_substitution=None
)
XMLFormatter.REGISTRY["html"] =  XMLFormatter(
    entity_substitution=EntitySubstitution.substitute_html
)
XMLFormatter.REGISTRY["minimal"] = XMLFormatter(
    entity_substitution=EntitySubstitution.substitute_xml
)
XMLFormatter.REGISTRY[None] = Formatter(
    Formatter(Formatter.XML, entity_substitution=None)
)
