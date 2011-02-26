try:
    from threading import currentThread
except ImportError:
    from dummy_threading import currentThread

from . import utils

_active = {}

def activate(tz):
    _active[currentThread()] = tz

def deactivate():
    global _active
    if currentThread() in _active:
        del _active[currentThread()]

def get_timezone():
    t = _active.get(currentThread(), None)
    if t is not None:
        return t

    from django.conf import settings
    return utils.coerce_timezone_value(settings.TIME_ZONE)

