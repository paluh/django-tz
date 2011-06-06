import datetime
import pytz

from django import forms
from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.widgets import MultiWidget
from django.forms.fields import MultiValueField, DateField, TimeField
from django.utils.translation import ugettext_lazy as _

from . import zones
from .utils import adjust_datetime_to_timezone, coerce_timezone_value
from . import global_tz

class TimeZoneField(forms.TypedChoiceField):
    def __init__(self, *args, **kwargs):
        if not "choices" in kwargs:
            kwargs["choices"] = zones.ALL_TIMEZONE_CHOICES
        kwargs["coerce"] = coerce_timezone_value
        super(TimeZoneField, self).__init__(*args, **kwargs)

class TimeZoneDateTimeWidget(MultiWidget):
    def decompress(self, value):
        if value:
            if not value.tzinfo:
                value = pytz.timezone('UTC').localize(value)
            return [value, value.tzinfo]
        return [None, None]

class TimeZoneDateTimeField(MultiValueField):
    """
    This field operates on datetime fields with tzinfo.
    If intial value has no tzinfo it assumes that it equals
    settings.TIME_ZONE.
    """
    widget = TimeZoneDateTimeWidget
    default_error_messages = {
        'invalid_datetime': _(u'Enter a valid date/time.'),
        'invalid_timezone': _(u'Invalid timezone.')
    }

    def __init__(self, input_datetime_formats=None, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        self.localize = kwargs.get('localize', True)
        fields = (
            forms.DateTimeField(input_formats=input_datetime_formats,
                      error_messages={'invalid': errors['invalid_datetime']},
                      localize=self.localize),
            TimeZoneField(error_messages={'invalid': errors['invalid_timezone']})
        )
        dtw = kwargs.pop('datetime_widget', fields[0].widget)
        tzw = kwargs.pop('timezone_widget', fields[1].widget)
        if isinstance(self.widget, type):
            self.widget = self.widget((dtw, tzw))
        super(TimeZoneDateTimeField, self).__init__(fields, *args, **kwargs)

    def clean(self, value):
        # validate subfields only when datetime value is not empty
        if (isinstance(value, (list, tuple)) and
            (not value or not [v for v in value[:-1] if v not in validators.EMPTY_VALUES])):
            return super(TimeZoneDateTimeField, self).clean([])
        return super(TimeZoneDateTimeField, self).clean(value)

    def compress(self, data_list):
        if data_list:
            # Raise a validation error if time or date is empty
            # (possible if SplitDateTimeField has required=False).
            if data_list[0] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_datetime'])
            if data_list[1] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_timezone'])
            return data_list[1].localize(data_list[0])
        return None

class LocalizedDateTimeWidget(TimeZoneDateTimeWidget):
    def __init__(self, *args, **kwargs):
        self.get_timezone = kwargs.get('get_timezone',
                    lambda value: global_tz.get_timezone())
        super(LocalizedDateTimeWidget, self).__init__(*args, **kwargs)

    def decompress(self, value):
        if value:
            if not value.tzinfo:
                value = pytz.timezone(settings.TIME_ZONE).localize(value)
            tz = self.get_timezone(value)
            value = adjust_datetime_to_timezone(value, value.tzinfo, tz)
            return super(LocalizedDateTimeWidget, self).decompress(value)
        return [None, self.get_timezone(value)]

class LocalizedDateTimeField(TimeZoneDateTimeField):
    """
    This field localizes datetime value by converting it to global_tz value
    and during cleanup transforms value to default tz (or to settings.TIME_ZONE).
    """
    widget = LocalizedDateTimeWidget

    def compress(self, *args, **kwargs):
        result = super(LocalizedDateTimeField, self).compress(*args, **kwargs)
        if result:
            result = adjust_datetime_to_timezone(result, result.tzinfo,
                        pytz.timezone(settings.TIME_ZONE)).replace(tzinfo=None)
        return result

class SplitLocalizedDateTimeWidget(LocalizedDateTimeWidget):
    def decompress(self, value):
        splited = super(SplitLocalizedDateTimeWidget, self).decompress(value)
        if splited[0]:
            return [splited[0].date(), splited[0].time().replace(microsecond=0), splited[1]]
        return [None, None, splited[1]]

class SplitLocalizedDateTimeField(MultiValueField):
    widget = SplitLocalizedDateTimeWidget

    default_error_messages = {
        'invalid_date': _(u'Enter a valid date.'),
        'invalid_time': _(u'Enter a valid time.'),
        'invalid_timezone': _(u'Invalid timezone.')
    }

    def __init__(self, input_date_formats=None, input_time_formats=None, *args, **kwargs):
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        self.localize = kwargs.get('localize', True)
        fields = (
            DateField(input_formats=input_date_formats,
                      error_messages={'invalid': errors['invalid_date']},
                      localize=self.localize),
            TimeField(input_formats=input_time_formats,
                      error_messages={'invalid': errors['invalid_time']},
                      localize=self.localize),
            TimeZoneField(error_messages={'invalid': errors['invalid_timezone']})
        )
        dw = kwargs.pop('date_widget', fields[0].widget)
        tw = kwargs.pop('time_widget', fields[1].widget)
        tzw = kwargs.pop('timezone_widget', fields[2].widget)
        if isinstance(self.widget, type):
            self.widget = self.widget((dw, tw, tzw))
        super(SplitLocalizedDateTimeField, self).__init__(fields, *args, **kwargs)

    def clean(self, value):
        # validate subfields only when date or time value are not empty
        if (isinstance(value, (list, tuple)) and
            (not value or not [v for v in value[:-1] if v not in validators.EMPTY_VALUES])):
            return super(SplitLocalizedDateTimeField, self).clean([])
        return super(SplitLocalizedDateTimeField, self).clean(value)

    def compress(self, data_list):
        if data_list:
            # Raise a validation error if time or date is empty
            # (possible if SplitDateTimeField has required=False).
            if data_list[0] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_date'])
            if data_list[1] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_time'])
            if data_list[2] in validators.EMPTY_VALUES:
                raise ValidationError(self.error_messages['invalid_timezone'])

            dt = datetime.datetime.combine(*data_list[:2])
            tz = data_list[2]
            if dt and tz:
                result = adjust_datetime_to_timezone(dt, tz,
                            pytz.timezone(settings.TIME_ZONE)).replace(tzinfo=None)
            return result
        return None

class TimeZoneForm(forms.Form):
    """Simple one field form used by middleware and in views."""
    timezone = TimeZoneField()

