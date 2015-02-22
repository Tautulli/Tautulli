Unidecode, lossy ASCII transliterations of Unicode text
=======================================================

It often happens that you have text data in Unicode, but you need to
represent it in ASCII. For example when integrating with legacy code that
doesn't support Unicode, or for ease of entry of non-Roman names on a US
keyboard, or when constructing ASCII machine identifiers from
human-readable Unicode strings that should still be somewhat intelligeble
(a popular example of this is when making an URL slug from an article
title). 

In most of these examples you could represent Unicode characters as
"???" or "\\15BA\\15A0\\1610", to mention two extreme cases. But that's
nearly useless to someone who actually wants to read what the text says.

What Unidecode provides is a middle road: function unidecode() takes
Unicode data and tries to represent it in ASCII characters (i.e., the
universally displayable characters between 0x00 and 0x7F), where the
compromises taken when mapping between two character sets are chosen to be
near what a human with a US keyboard would choose.

The quality of resulting ASCII representation varies. For languages of
western origin it should be between perfect and good. On the other hand
transliteration (i.e., conveying, in Roman letters, the pronunciation
expressed by the text in some other writing system) of languages like
Chinese, Japanese or Korean is a very complex issue and this library does
not even attempt to address it. It draws the line at context-free
character-by-character mapping. So a good rule of thumb is that the further
the script you are transliterating is from Latin alphabet, the worse the
transliteration will be.

Note that this module generally produces better results than simply
stripping accents from characters (which can be done in Python with
built-in functions). It is based on hand-tuned character mappings that for
example also contain ASCII approximations for symbols and non-Latin
alphabets.

This is a Python port of Text::Unidecode Perl module by
Sean M. Burke <sburke@cpan.org>.


Module content
--------------

The module exports a single function that takes an Unicode object (Python
2.x) or string (Python 3.x) and returns a string (that can be encoded to
ASCII bytes in Python 3.x)::

    >>> from unidecode import unidecode
    >>> unidecode(u'ko\u017eu\u0161\u010dek')
    'kozuscek'
    >>> unidecode(u'30 \U0001d5c4\U0001d5c6/\U0001d5c1')
    '30 km/h'
    >>> unidecode(u"\u5317\u4EB0")
    'Bei Jing '


Requirements
------------

Nothing except Python itself.
    
You need a Python build with "wide" Unicode characters (also called "UCS-4
build") in order for unidecode to work correctly with characters outside of
Basic Multilingual Plane (BMP). Common characters outside BMP are bold, italic,
script, etc. variants of the Latin alphabet intended for mathematical notation.
Surrogate pair encoding of "narrow" builds is not supported in unidecode.

If your Python build supports "wide" Unicode the following expression will
return True::

    >>> import sys
    >>> sys.maxunicode > 0xffff
    True

See PEP 261 for details regarding support for "wide" Unicode characters in
Python.


Installation
------------

You install Unidecode, as you would install any Python module, by running
these commands::

    python setup.py install
    python setup.py test


Source
------

You can get the latest development version of Unidecode with::

    git clone https://www.tablix.org/~avian/git/unidecode.git


Support
-------

Questions, bug reports, useful code bits, and suggestions for Unidecode
should be sent to tomaz.solc@tablix.org


Copyright
---------

Original character transliteration tables:

Copyright 2001, Sean M. Burke <sburke@cpan.org>, all rights reserved.

Python code and later additions:

Copyright 2014, Tomaz Solc <tomaz.solc@tablix.org>

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation; either version 2 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc., 51
Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.  The programs and
documentation in this dist are distributed in the hope that they will be
useful, but without any warranty; without even the implied warranty of
merchantability or fitness for a particular purpose.

..
    vim: set filetype=rst:
