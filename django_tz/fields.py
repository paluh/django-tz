import datetime
import pytz

from django.conf import settings
from django.db import models
from django.db.models import signals
from django.utils.encoding import smart_unicode, smart_str

from . import forms, zones
from .utils import coerce_timezone_value, validate_timezone_max_length, adjust_datetime_to_timezone
from . import global_tz

MAX_TIMEZONE_LENGTH = getattr(settings, "MAX_TIMEZONE_LENGTH", 100)

class TimeZoneField(models.CharField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        validate_timezone_max_length(MAX_TIMEZONE_LENGTH, zones.ALL_TIMEZONE_CHOICES)
        defaults = {
            "max_length": MAX_TIMEZONE_LENGTH,
            "default": global_tz.get_timezone,
            "choices": zones.PRETTY_TIMEZONE_CHOICES
        }
        defaults.update(kwargs)
        return super(TimeZoneField, self).__init__(*args, **defaults)

    def validate(self, value, model_instance):
        # coerce value back to a string to validate correctly
        return super(TimeZoneField, self).validate(smart_str(value), model_instance)

    def run_validators(self, value):
        # coerce value back to a string to validate correctly
        return super(TimeZoneField, self).run_validators(smart_str(value))

    def to_python(self, value):
        value = super(TimeZoneField, self).to_python(value)
        if value is None:
            return None # null=True
        return coerce_timezone_value(value)

    def get_prep_value(self, value):
        if value is not None:
            return smart_unicode(value)
        return value

    def get_db_prep_save(self, value, connection=None):
        """
        Prepares the given value for insertion into the database.
        """
        return self.get_prep_value(value)

    def flatten_data(self, follow, obj=None):
        value = self._get_val_from_obj(obj)
        if value is None:
            value = ""
        return {self.attname: smart_unicode(value)}

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(rules=[((TimeZoneField, ), [], {'max_length': ('max_length', {'default': MAX_TIMEZONE_LENGTH}),}),],
                                patterns=['timezones\.fields\.'])
except ImportError:
    pass
