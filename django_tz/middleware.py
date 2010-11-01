import pytz

from django.conf import settings
from django.utils.cache import patch_vary_headers
from django.utils.translation import trans_real

from . import global_tz
from .utils import guess_tz_from_lang

class TimezoneMiddleware(object):
    """
    This middleware guesses timezone from language and sets it in current
    thread global cache.
    """
    def process_request(self, request):
        accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        langs = trans_real.parse_accept_lang_header(accept_lang)
        for lang, unused in langs:
            tz = guess_tz_from_lang(lang)
            if tz:
                break
        else:
            tz = pytz.timezone(settings.TIME_ZONE)
        global_tz.activate(tz)

    def process_response(self, request, response):
        global_tz.deactivate()
        return response
