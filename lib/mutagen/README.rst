Mutagen
=======

Mutagen is a Python module to handle audio metadata. It supports ASF, FLAC, 
M4A, Monkey's Audio, MP3, Musepack, Ogg Opus, Ogg FLAC, Ogg Speex, Ogg 
Theora, Ogg Vorbis, True Audio, WavPack, OptimFROG, and AIFF audio files. 
All versions of ID3v2 are supported, and all standard ID3v2.4 frames are 
parsed. It can read Xing headers to accurately calculate the bitrate and 
length of MP3s. ID3 and APEv2 tags can be edited regardless of audio 
format. It can also manipulate Ogg streams on an individual packet/page 
level.

Mutagen works on Python 2.6, 2.7, 3.3, 3.4 (CPython and PyPy) and has no 
dependencies outside the Python standard library.


Installing
----------

 $ ./setup.py build
 $ su -c "./setup.py install"


Documentation
-------------

The primary documentation for Mutagen is the doc strings found in
the source code and the sphinx documentation in the docs/ directory.

To build the docs (needs sphinx):

 $ ./setup.py build_sphinx

The tools/ directory contains several useful examples.

The docs are also hosted on readthedocs.org:

 http://mutagen.readthedocs.org


Testing the Module
------------------

To test Mutagen's MP3 reading support, run
 $ tools/mutagen-pony <your top-level MP3 directory here>
Mutagen will try to load all of them, and report any errors.

To look at the tags in files, run
 $ tools/mutagen-inspect filename ...

To run our test suite,
 $ ./setup.py test


Compatibility/Bugs
------------------

See docs/bugs.rst
