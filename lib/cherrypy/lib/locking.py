import datetime


class NeverExpires(object):
    def expired(self):
        return False


class Timer(object):
    """
    A simple timer that will indicate when an expiration time has passed.
    """
    def __init__(self, expiration):
        "Create a timer that expires at `expiration` (UTC datetime)"
        self.expiration = expiration

    @classmethod
    def after(cls, elapsed):
        """
        Return a timer that will expire after `elapsed` passes.
        """
        return cls(datetime.datetime.utcnow() + elapsed)

    def expired(self):
        return datetime.datetime.utcnow() >= self.expiration


class LockTimeout(Exception):
    "An exception when a lock could not be acquired before a timeout period"


class LockChecker(object):
    """
    Keep track of the time and detect if a timeout has expired
    """
    def __init__(self, session_id, timeout):
        self.session_id = session_id
        if timeout:
            self.timer = Timer.after(timeout)
        else:
            self.timer = NeverExpires()

    def expired(self):
        if self.timer.expired():
            raise LockTimeout(
                "Timeout acquiring lock for %(session_id)s" % vars(self))
        return False
