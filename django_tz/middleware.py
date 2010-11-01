import pytz

from django.conf import settings
from django.utils.cache import patch_vary_headers
from django.utils import translation

from . import global_tz
from .utils import guess_tz_from_lang

class TimezoneMiddleware(object):
    """
    This middleware guesses timezone from language and sets it in current
    thread global cache.
    """
    def process_request(self, request):
        lang = translation.get_language()
        tz = guess_tz_from_lang(lang)
        global_tz.activate(tz)

    def process_response(self, request, response):
        global_tz.deactivate()
        return response
