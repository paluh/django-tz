import pytz

from django.conf import settings
from django.template import Node
from django.template import Library

from django_tz.utils import adjust_datetime_to_timezone
from django_tz import global_tz

register = Library()

@register.filter
def to_global_tz(value, from_timezone=None):
    with_tzinfo = value.tzinfo is not None
    from_timezone = from_timezone or value.tzinfo or pytz.timezone(settings.TIME_ZONE)
    value = adjust_datetime_to_timezone(value, from_timezone, global_tz.get_timezone())
    if with_tzinfo:
        return value
    return value.replace(tzinfo=None)

