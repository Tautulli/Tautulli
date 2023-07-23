"""Publish-subscribe bus tests."""
# pylint: disable=redefined-outer-name

import os
import sys
import threading
import time
import unittest.mock

import pytest

from cherrypy.process import wspbus


CI_ON_MACOS = bool(os.getenv('CI')) and sys.platform == 'darwin'
msg = 'Listener %d on channel %s: %s.'  # pylint: disable=invalid-name


@pytest.fixture
def bus():
    """Return a wspbus instance."""
    return wspbus.Bus()


@pytest.fixture
def log_tracker(bus):
    """Return an instance of bus log tracker."""
    class LogTracker:  # pylint: disable=too-few-public-methods
        """Bus log tracker."""

        log_entries = []

        def __init__(self, bus):
            def logit(msg, level):  # pylint: disable=unused-argument
                self.log_entries.append(msg)
            bus.subscribe('log', logit)

    return LogTracker(bus)


@pytest.fixture
def listener():
    """Return an instance of bus response tracker."""
    class Listner:  # pylint: disable=too-few-public-methods
        """Bus handler return value tracker."""

        responses = []

        def get_listener(self, channel, index):
            """Return an argument tracking listener."""
            def listener(arg=None):
                self.responses.append(msg % (index, channel, arg))
            return listener

    return Listner()


def test_builtin_channels(bus, listener):
    """Test that built-in channels trigger corresponding listeners."""
    expected = []

    for channel in bus.listeners:
        for index, priority in enumerate([100, 50, 0, 51]):
            bus.subscribe(
                channel,
                listener.get_listener(channel, index),
                priority,
            )

    for channel in bus.listeners:
        bus.publish(channel)
        expected.extend([msg % (i, channel, None) for i in (2, 1, 3, 0)])
        bus.publish(channel, arg=79347)
        expected.extend([msg % (i, channel, 79347) for i in (2, 1, 3, 0)])

    assert listener.responses == expected


def test_custom_channels(bus, listener):
    """Test that custom pub-sub channels work as built-in ones."""
    expected = []

    custom_listeners = ('hugh', 'louis', 'dewey')
    for channel in custom_listeners:
        for index, priority in enumerate([None, 10, 60, 40]):
            bus.subscribe(
                channel,
                listener.get_listener(channel, index),
                priority,
            )

    for channel in custom_listeners:
        bus.publish(channel, 'ah so')
        expected.extend(msg % (i, channel, 'ah so') for i in (1, 3, 0, 2))
        bus.publish(channel)
        expected.extend(msg % (i, channel, None) for i in (1, 3, 0, 2))

    assert listener.responses == expected


def test_listener_errors(bus, listener):
    """Test that unhandled exceptions raise channel failures."""
    expected = []
    channels = [c for c in bus.listeners if c != 'log']

    for channel in channels:
        bus.subscribe(channel, listener.get_listener(channel, 1))
        # This will break since the lambda takes no args.
        bus.subscribe(channel, lambda: None, priority=20)

    for channel in channels:
        with pytest.raises(wspbus.ChannelFailures):
            bus.publish(channel, 123)
        expected.append(msg % (1, channel, 123))

    assert listener.responses == expected


def test_start(bus, listener, log_tracker):
    """Test that bus start sequence calls all listeners."""
    num = 3
    for index in range(num):
        bus.subscribe('start', listener.get_listener('start', index))

    bus.start()
    try:
        # The start method MUST call all 'start' listeners.
        assert (
            set(listener.responses) ==
            set(msg % (i, 'start', None) for i in range(num)))
        # The start method MUST move the state to STARTED
        # (or EXITING, if errors occur)
        assert bus.state == bus.states.STARTED
        # The start method MUST log its states.
        assert log_tracker.log_entries == ['Bus STARTING', 'Bus STARTED']
    finally:
        # Exit so the atexit handler doesn't complain.
        bus.exit()


def test_stop(bus, listener, log_tracker):
    """Test that bus stop sequence calls all listeners."""
    num = 3

    for index in range(num):
        bus.subscribe('stop', listener.get_listener('stop', index))

    bus.stop()

    # The stop method MUST call all 'stop' listeners.
    assert (set(listener.responses) ==
            set(msg % (i, 'stop', None) for i in range(num)))

    # The stop method MUST move the state to STOPPED
    assert bus.state == bus.states.STOPPED

    # The stop method MUST log its states.
    assert log_tracker.log_entries == ['Bus STOPPING', 'Bus STOPPED']


def test_graceful(bus, listener, log_tracker):
    """Test that bus graceful state triggers all listeners."""
    num = 3

    for index in range(num):
        bus.subscribe('graceful', listener.get_listener('graceful', index))

    bus.graceful()

    # The graceful method MUST call all 'graceful' listeners.
    assert (
        set(listener.responses) ==
        set(msg % (i, 'graceful', None) for i in range(num)))

    # The graceful method MUST log its states.
    assert log_tracker.log_entries == ['Bus graceful']


def test_exit(bus, listener, log_tracker):
    """Test that bus exit sequence is correct."""
    num = 3

    for index in range(num):
        bus.subscribe('stop', listener.get_listener('stop', index))
        bus.subscribe('exit', listener.get_listener('exit', index))

    bus.exit()

    # The exit method MUST call all 'stop' listeners,
    # and then all 'exit' listeners.
    assert (set(listener.responses) ==
            set([msg % (i, 'stop', None) for i in range(num)] +
                [msg % (i, 'exit', None) for i in range(num)]))

    # The exit method MUST move the state to EXITING
    assert bus.state == bus.states.EXITING

    # The exit method MUST log its states.
    assert (log_tracker.log_entries ==
            ['Bus STOPPING', 'Bus STOPPED', 'Bus EXITING', 'Bus EXITED'])


def test_wait(bus):
    """Test that bus wait awaits for states."""
    def f(method):  # pylint: disable=invalid-name
        time.sleep(0.2)
        getattr(bus, method)()

    flow = [
        ('start', [bus.states.STARTED]),
        ('stop', [bus.states.STOPPED]),
        ('start', [bus.states.STARTING, bus.states.STARTED]),
        ('exit', [bus.states.EXITING]),
    ]

    for method, states in flow:
        threading.Thread(target=f, args=(method,)).start()
        bus.wait(states)

        # The wait method MUST wait for the given state(s).
        assert bus.state in states, 'State %r not in %r' % (bus.state, states)


@pytest.mark.xfail(CI_ON_MACOS, reason='continuous integration on macOS fails')
def test_wait_publishes_periodically(bus):
    """Test that wait publishes each tick."""
    callback = unittest.mock.MagicMock()
    bus.subscribe('main', callback)

    def set_start():
        time.sleep(0.05)
        bus.start()
    threading.Thread(target=set_start).start()
    bus.wait(bus.states.STARTED, interval=0.01, channel='main')
    assert callback.call_count > 3


def test_block(bus, log_tracker):
    """Test that bus block waits for exiting."""
    def f():  # pylint: disable=invalid-name
        time.sleep(0.2)
        bus.exit()

    def g():  # pylint: disable=invalid-name
        time.sleep(0.4)

    threading.Thread(target=f).start()
    threading.Thread(target=g).start()
    threads = [t for t in threading.enumerate() if not t.daemon]
    assert len(threads) == 3

    bus.block()

    # The block method MUST wait for the EXITING state.
    assert bus.state == bus.states.EXITING

    # The block method MUST wait for ALL non-main, non-daemon threads to
    # finish.
    threads = [t for t in threading.enumerate() if not t.daemon]
    assert len(threads) == 1

    # The last message will mention an indeterminable thread name; ignore
    # it
    expected_bus_messages = [
        'Bus STOPPING',
        'Bus STOPPED',
        'Bus EXITING',
        'Bus EXITED',
        'Waiting for child threads to terminate...',
    ]
    bus_msg_num = len(expected_bus_messages)

    # If the last message mentions an indeterminable thread name then ignore it
    assert log_tracker.log_entries[:bus_msg_num] == expected_bus_messages
    assert len(log_tracker.log_entries[bus_msg_num:]) <= 1, (
        'No more than one extra log line with the thread name expected'
    )


def test_start_with_callback(bus):
    """Test that callback fires on bus start."""
    try:
        events = []

        def f(*args, **kwargs):  # pylint: disable=invalid-name
            events.append(('f', args, kwargs))

        def g():  # pylint: disable=invalid-name
            events.append('g')
        bus.subscribe('start', g)
        bus.start_with_callback(f, (1, 3, 5), {'foo': 'bar'})

        # Give wait() time to run f()
        time.sleep(0.2)

        # The callback method MUST wait for the STARTED state.
        assert bus.state == bus.states.STARTED

        # The callback method MUST run after all start methods.
        assert events == ['g', ('f', (1, 3, 5), {'foo': 'bar'})]
    finally:
        bus.exit()


def test_log(bus, log_tracker):
    """Test that bus messages and errors are logged."""
    assert log_tracker.log_entries == []

    # Try a normal message.
    expected = []
    for msg_ in ["O mah darlin'"] * 3 + ['Clementiiiiiiiine']:
        bus.log(msg_)
        expected.append(msg_)
        assert log_tracker.log_entries == expected

    # Try an error message
    try:
        foo
    except NameError:
        bus.log('You are lost and gone forever', traceback=True)
        lastmsg = log_tracker.log_entries[-1]
        assert 'Traceback' in lastmsg and 'NameError' in lastmsg, (
            'Last log message %r did not contain '
            'the expected traceback.' % lastmsg
        )
    else:
        pytest.fail('NameError was not raised as expected.')
