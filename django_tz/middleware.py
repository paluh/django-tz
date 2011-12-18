import datetime
import pytz

from django.conf import settings
from django.utils.cache import patch_vary_headers
from django.utils.translation import trans_real

from . import global_tz
from .forms import TimeZoneForm
from .utils import guess_tz_from_lang

def get_tz_from_request(request):
    if hasattr(request, 'session'):
        session_name = getattr(settings, 'TIMEZONE_SESSION_NAME', 'django_timezone')
        tz = request.session.get(session_name, None)
        if tz and isinstance(tz, datetime.tzinfo):
            return tz

    cookie_name = getattr(settings, 'TIMEZONE_COOKIE_NAME', 'TIMEZONE')
    form = TimeZoneForm({'timezone': request.COOKIES.get(cookie_name, None)})
    if form.is_valid():
        return form.cleaned_data['timezone']

    return None

class GlobalTimezoneMiddleware(object):
    """
    This middleware guesses timezone from language and sets it in current
    thread global cache.
    """
    def get_tz(self, request):
        raise NotImplementedError()

    def process_request(self, request):
        tz = self.get_tz(request)
        if tz:
            global_tz.activate(tz)

    def process_response(self, request, response):
        global_tz.deactivate()
        return response

class TimezoneFromLangMiddleware(GlobalTimezoneMiddleware):
    """
    Not very smart middelware which guesses timezone from request lang setting.
    """
    def get_tz(self, request):
        tz = get_tz_from_request(request)
        if tz:
            return tz

        accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        langs = trans_real.parse_accept_lang_header(accept_lang)
        for lang, unused in langs:
            tz = guess_tz_from_lang(lang)
            if tz:
                break
        return tz

