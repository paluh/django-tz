import pytz.tzinfo

from django.db import models
from django.utils.encoding import smart_unicode, smart_str

from . import forms
from . import global_tz
from . import zones
from .utils import coerce_timezone_value


class TimeZoneField(models.CharField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        defaults = {
            "max_length": max(len(v) for (v,n) in zones.ALL_TIMEZONE_CHOICES),
            "default": global_tz.get_timezone,
            "choices": zones.ALL_TIMEZONE_CHOICES
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

    def formfield(self, form_class=forms.TimeZoneField, **kwargs):
        return super(TimeZoneField, self).formfield(form_class=form_class, **kwargs)

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(
        rules=[
            ((TimeZoneField, ), [], {
              'max_length': ('max_length', {}),
              'default': ('default',
                          {'converter': (lambda v: v.zone if isinstance(v, pytz.tzinfo.tzinfo) else v)})
            })
        ],
        patterns=['django_tz\.fields\.']
    )
except ImportError:
    pass
