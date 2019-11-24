import six

import cherrypy
from cherrypy.test import helper


class IteratorBase(object):

    created = 0
    datachunk = 'butternut squash' * 256

    @classmethod
    def incr(cls):
        cls.created += 1

    @classmethod
    def decr(cls):
        cls.created -= 1


class OurGenerator(IteratorBase):

    def __iter__(self):
        self.incr()
        try:
            for i in range(1024):
                yield self.datachunk
        finally:
            self.decr()


class OurIterator(IteratorBase):

    started = False
    closed_off = False
    count = 0

    def increment(self):
        self.incr()

    def decrement(self):
        if not self.closed_off:
            self.closed_off = True
            self.decr()

    def __iter__(self):
        return self

    def __next__(self):
        if not self.started:
            self.started = True
            self.increment()
        self.count += 1
        if self.count > 1024:
            raise StopIteration
        return self.datachunk

    next = __next__

    def __del__(self):
        self.decrement()


class OurClosableIterator(OurIterator):

    def close(self):
        self.decrement()


class OurNotClosableIterator(OurIterator):

    # We can't close something which requires an additional argument.
    def close(self, somearg):
        self.decrement()


class OurUnclosableIterator(OurIterator):
    close = 'close'  # not callable!


class IteratorTest(helper.CPWebCase):

    @staticmethod
    def setup_server():

        class Root(object):

            @cherrypy.expose
            def count(self, clsname):
                cherrypy.response.headers['Content-Type'] = 'text/plain'
                return six.text_type(globals()[clsname].created)

            @cherrypy.expose
            def getall(self, clsname):
                cherrypy.response.headers['Content-Type'] = 'text/plain'
                return globals()[clsname]()

            @cherrypy.expose
            @cherrypy.config(**{'response.stream': True})
            def stream(self, clsname):
                return self.getall(clsname)

        cherrypy.tree.mount(Root())

    def test_iterator(self):
        try:
            self._test_iterator()
        except Exception:
            'Test fails intermittently. See #1419'

    def _test_iterator(self):
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        # Check the counts of all the classes, they should be zero.
        closables = ['OurClosableIterator', 'OurGenerator']
        unclosables = ['OurUnclosableIterator', 'OurNotClosableIterator']
        all_classes = closables + unclosables

        import random
        random.shuffle(all_classes)

        for clsname in all_classes:
            self.getPage('/count/' + clsname)
            self.assertStatus(200)
            self.assertBody('0')

        # We should also be able to read the entire content body
        # successfully, though we don't need to, we just want to
        # check the header.
        for clsname in all_classes:
            itr_conn = self.get_conn()
            itr_conn.putrequest('GET', '/getall/' + clsname)
            itr_conn.endheaders()
            response = itr_conn.getresponse()
            self.assertEqual(response.status, 200)
            headers = response.getheaders()
            for header_name, header_value in headers:
                if header_name.lower() == 'content-length':
                    expected = six.text_type(1024 * 16 * 256)
                    assert header_value == expected, header_value
                    break
            else:
                raise AssertionError('No Content-Length header found')

            # As the response should be fully consumed by CherryPy
            # before sending back, the count should still be at zero
            # by the time the response has been sent.
            self.getPage('/count/' + clsname)
            self.assertStatus(200)
            self.assertBody('0')

        # Now we do the same check with streaming - some classes will
        # be automatically closed, while others cannot.
        stream_counts = {}
        for clsname in all_classes:
            itr_conn = self.get_conn()
            itr_conn.putrequest('GET', '/stream/' + clsname)
            itr_conn.endheaders()
            response = itr_conn.getresponse()
            self.assertEqual(response.status, 200)
            response.fp.read(65536)

            # Let's check the count - this should always be one.
            self.getPage('/count/' + clsname)
            self.assertBody('1')

            # Now if we close the connection, the count should go back
            # to zero.
            itr_conn.close()
            self.getPage('/count/' + clsname)

            # If this is a response which should be easily closed, then
            # we will test to see if the value has gone back down to
            # zero.
            if clsname in closables:

                # Sometimes we try to get the answer too quickly - we
                # will wait for 100 ms before asking again if we didn't
                # get the answer we wanted.
                if self.body != '0':
                    import time
                    time.sleep(0.1)
                    self.getPage('/count/' + clsname)

            stream_counts[clsname] = int(self.body)

        # Check that we closed off the classes which should provide
        # easy mechanisms for doing so.
        for clsname in closables:
            assert stream_counts[clsname] == 0, (
                'did not close off stream response correctly, expected '
                'count of zero for %s: %s' % (clsname, stream_counts)
            )
