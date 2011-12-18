import pytz

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_str

def adjust_datetime_to_timezone(value, from_tz, to_tz=None):
    """
    Given a ``datetime`` object adjust it according to the from_tz timezone
    string into the to_tz timezone string.
    """
    if to_tz is None:
        to_tz = settings.TIME_ZONE
    if value.tzinfo is None:
        if not hasattr(from_tz, "localize"):
            from_tz = pytz.timezone(smart_str(from_tz))
        value = from_tz.localize(value)
    tz = pytz.timezone(smart_str(to_tz))
    return tz.normalize(value.astimezone(tz))

def coerce_timezone_value(value):
    try:
        return pytz.timezone(value)
    except pytz.UnknownTimeZoneError:
        raise ValidationError("Unknown timezone")

def guess_tz_from_lang(language_code):
    country_code = language_code.split('-', 1)[1] if '-' in language_code else language_code
    if country_code.upper() in pytz.country_timezones:
        return pytz.country_timezones[country_code][0]
    return None
