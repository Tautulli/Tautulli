"""CherryPy Library"""

# Deprecated in CherryPy 3.2 -- remove in CherryPy 3.3
from cherrypy.lib.reprconf import unrepr, modules, attributes

def is_iterator(obj):
    '''Returns a boolean indicating if the object provided implements
     the iterator protocol (i.e. like a generator). This will return
     false for objects which iterable, but not iterators themselves.'''
    from types import GeneratorType
    if isinstance(obj, GeneratorType):
        return True
    elif not hasattr(obj, '__iter__'):
        return False
    else:
        # Types which implement the protocol must return themselves when
        # invoking 'iter' upon them.
        return iter(obj) is obj
        
def is_closable_iterator(obj):
    
    # Not an iterator.
    if not is_iterator(obj):
        return False
    
    # A generator - the easiest thing to deal with.
    import inspect
    if inspect.isgenerator(obj):
        return True
    
    # A custom iterator. Look for a close method...
    if not (hasattr(obj, 'close') and callable(obj.close)):
        return False
    
    #  ... which doesn't require any arguments.
    try:
        inspect.getcallargs(obj.close)
    except TypeError:
        return False
    else:
        return True

class file_generator(object):

    """Yield the given input (a file object) in chunks (default 64k). (Core)"""

    def __init__(self, input, chunkSize=65536):
        self.input = input
        self.chunkSize = chunkSize

    def __iter__(self):
        return self

    def __next__(self):
        chunk = self.input.read(self.chunkSize)
        if chunk:
            return chunk
        else:
            if hasattr(self.input, 'close'):
                self.input.close()
            raise StopIteration()
    next = __next__


def file_generator_limited(fileobj, count, chunk_size=65536):
    """Yield the given file object in chunks, stopping after `count`
    bytes has been emitted.  Default chunk size is 64kB. (Core)
    """
    remaining = count
    while remaining > 0:
        chunk = fileobj.read(min(chunk_size, remaining))
        chunklen = len(chunk)
        if chunklen == 0:
            return
        remaining -= chunklen
        yield chunk


def set_vary_header(response, header_name):
    "Add a Vary header to a response"
    varies = response.headers.get("Vary", "")
    varies = [x.strip() for x in varies.split(",") if x.strip()]
    if header_name not in varies:
        varies.append(header_name)
    response.headers['Vary'] = ", ".join(varies)
