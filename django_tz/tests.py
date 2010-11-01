import re

from datetime import datetime

import pytz

from django import forms
from django.conf import settings
from django.db import models
from django.forms.models import model_to_dict
from django.forms.widgets import HiddenInput
from django.http import HttpRequest
from django.test import TestCase
from django.utils import translation

from .fields import TimeZoneField
from . import forms as tz_forms
from . import global_tz
from . import middleware

from .utils import adjust_datetime_to_timezone, guess_tz_from_lang

#model for tests
class Profile(models.Model):
    name = models.CharField(max_length=100)
    timezone = TimeZoneField(blank=True, null=True)
    joined = models.DateTimeField(blank=True, null=True)

class TimeZoneTestCase(TestCase):
    def setUp(self):
        # ensure UTC
        self.ORIGINAL_TIME_ZONE = settings.TIME_ZONE
        settings.TIME_ZONE = "UTC"

    def tearDown(self):
        settings.TIME_ZONE = self.ORIGINAL_TIME_ZONE

    # little helpers
    def assertFormIsValid(self, form):
        is_valid = form.is_valid()
        self.assert_(is_valid,
            "Form did not validate (errors=%r, form=%r)" % (form._errors, form)
        )

class UtilsTestCase(TimeZoneTestCase):
    def test_adjust_datetime_to_timezone(self):
        self.assertEqual(
            adjust_datetime_to_timezone(
                datetime(2008, 6, 25, 18, 0, 0), "UTC"
            ).strftime("%m/%d/%Y %H:%M:%S"),
            "06/25/2008 18:00:00"
        )

    def test_tz_guessing(self):
        try:
            request = HttpRequest()
            request.META['HTTP_ACCEPT_LANGUAGE'] = 'en-ca,en;q=0.8,en-us;q=0.6,de-de;q=0.4,de;q=0.2'
            middleware.TimezoneMiddleware().process_request(request)
            self.assertEqual(global_tz.get_timezone(), pytz.country_timezones['ca'][0])

            request.META['HTTP_ACCEPT_LANGUAGE'] = 'pl,en;q=0.8,en-us;q=0.6,de-de;q=0.4,de;q=0.2'
            middleware.TimezoneMiddleware().process_request(request)
            self.assertEqual(global_tz.get_timezone(), pytz.country_timezones['pl'][0])
        finally:
            global_tz.deactivate()

class TimeZoneFieldTestCase(TimeZoneTestCase):
    def test_forms_clean_required(self):
        f = tz_forms.TimeZoneField()
        self.assertEqual(
            repr(f.clean("US/Eastern")),
            "<DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>"
        )
        self.assertRaises(forms.ValidationError, f.clean, "")

    def test_forms_clean_not_required(self):
        f = tz_forms.TimeZoneField(required=False)
        self.assertEqual(
            repr(f.clean("US/Eastern")),
            "<DstTzInfo 'US/Eastern' EST-1 day, 19:00:00 STD>"
        )
        self.assertEqual(f.clean(""), "")

    def test_forms_clean_bad_value(self):
        f = tz_forms.TimeZoneField()
        try:
            f.clean("BAD VALUE")
        except forms.ValidationError, e:
            self.assertEqual(e.messages, ["Select a valid choice. BAD VALUE is not one of the available choices."])

    def test_models_as_a_form(self):
        class ProfileForm(forms.ModelForm):
            class Meta:
                model = Profile
        form = ProfileForm()
        rendered = form.as_p()
        self.assert_(
            bool(re.search(r'<option value="[\w/]+">\([A-Z]+(?:\+|\-)\d{4}\)\s[\w/]+</option>', rendered)),
            "Did not find pattern in rendered form"
        )

    def test_models_modelform_validation(self):
        class ProfileForm(forms.ModelForm):
            class Meta:
                model = Profile
        form = ProfileForm({"name": "Brian Rosner", "timezone": "America/Denver"})
        self.assertFormIsValid(form)

    def test_models_modelform_save(self):
        class ProfileForm(forms.ModelForm):
            class Meta:
                model = Profile
        form = ProfileForm({"name": "Brian Rosner", "timezone": "America/Denver"})
        self.assertFormIsValid(form)
        p = form.save()

    def test_models_string_value(self):
        p = Profile(name="Brian Rosner", timezone="America/Denver")
        p.save()
        p = Profile.objects.get(pk=p.pk)
        self.assertEqual(p.timezone, pytz.timezone("America/Denver"))

    def test_models_string_value_lookup(self):
        Profile(name="Brian Rosner", timezone="America/Denver").save()
        qs = Profile.objects.filter(timezone="America/Denver")
        self.assertEqual(qs.count(), 1)

    def test_models_tz_value(self):
        tz = pytz.timezone("America/Denver")
        p = Profile(name="Brian Rosner", timezone=tz)
        p.save()
        p = Profile.objects.get(pk=p.pk)
        self.assertEqual(p.timezone, tz)

    def test_models_tz_value_lookup(self):
        Profile(name="Brian Rosner", timezone="America/Denver").save()
        qs = Profile.objects.filter(timezone=pytz.timezone("America/Denver"))
        self.assertEqual(qs.count(), 1)

class TimeZoneDateTimeFieldsTests(TimeZoneTestCase):
    def test_timezonedatetimefield_processing(self):
        class ProfileForm(forms.ModelForm):
            joined = tz_forms.TimeZoneDateTimeField()
            class Meta:
                fields = ('joined',)
                model = Profile

        joined = datetime(2010, 10, 28, 19)
        profile = Profile.objects.create(name="Tomasz Rybarczyk", joined=joined)
        form = ProfileForm(instance=profile, data={'joined_0': joined, 'joined_1': 'Europe/Warsaw'})
        profile = form.save()
        tz = pytz.timezone('Europe/Warsaw')
        self.assertEqual(profile.joined, tz.localize(joined))

    def test_localizeddatetimefield_display(self):
        g_tz = pytz.timezone('Europe/Warsaw')
        #lets say that user has Poland time in profile so middleware sets global value to this tz
        global_tz.activate(g_tz)
        try:
            class ProfileForm(forms.ModelForm):
                joined = tz_forms.LocalizedDateTimeField()
                class Meta:
                    fields = ('joined',)
                    model = Profile

            #Tomasz joined at 19 in UTC (setUp sets settings.TIME_ZONE to UTC)
            joined = datetime(2010, 10, 28, 19)
            profile = Profile.objects.create(name="Tomasz Rybarczyk", joined=joined)
            form = ProfileForm(instance=profile)
            #because global_tz is Europe/Warsaw values should be localized to this
            form_html = form.as_p()
            self.assertTrue('<input type="text" name="joined_0" value="2010-10-28 21:00:00"' in form_html)
            self.assertTrue('<option value="Europe/Warsaw" selected="selected">' in form_html)
        finally:
            global_tz.deactivate()

    def test_localizeddatetimefield_processing(self):
        class ProfileForm(forms.ModelForm):
            joined = tz_forms.LocalizedDateTimeField()
            class Meta:
                fields = ('joined',)
                model = Profile

        joined = datetime(2010, 10, 28, 19)
        profile = Profile.objects.create(name="Tomasz Rybarczyk", joined=joined)
        form = ProfileForm(instance=profile, data={'joined_0': joined, 'joined_1': 'Europe/Warsaw'})
        profile = form.save()
        self.assertEqual(profile.joined.tzinfo, None)

        tz = pytz.timezone('Europe/Warsaw')
        self.assertEqual(profile.joined, adjust_datetime_to_timezone(joined, tz, pytz.timezone(settings.TIME_ZONE)).replace(tzinfo=None))

    def test_splitimezonedatetimefield_processing(self):
        class ProfileForm(forms.ModelForm):
            joined = tz_forms.SplitLocalizedDateTimeField()
            class Meta:
                fields = ('joined',)
                model = Profile

        joined = datetime(2010, 10, 28, 19)
        profile = Profile.objects.create(name="Tomasz Rybarczyk", joined=joined)

        joined = datetime(2010, 10, 28, 18)
        form = ProfileForm(instance=profile, data={'joined_0': joined.date(),
                    'joined_1': joined.time().replace(microsecond=0), 'joined_2': 'Europe/Warsaw'})
        form.is_valid()
        profile = form.save()
        tz = pytz.timezone('Europe/Warsaw')
        self.assertEqual(profile.joined, adjust_datetime_to_timezone(joined, tz, pytz.timezone(settings.TIME_ZONE)).replace(tzinfo=None))

    def test_splitimezonedatetimefield_display_with_hidden_timezone(self):
        g_tz = pytz.timezone('Europe/Warsaw')
        #lets say that user has Poland time in profile so middleware sets global value to this tz
        global_tz.activate(g_tz)
        try:
            class ProfileForm(forms.ModelForm):
                joined = tz_forms.SplitLocalizedDateTimeField(timezone_widget=HiddenInput)
                class Meta:
                    fields = ('joined',)
                    model = Profile

            #Tomasz joined at 19 in UTC (setUp sets settings.TIME_ZONE to UTC)
            joined = datetime(2010, 10, 28, 19)
            profile = Profile.objects.create(name="Tomasz Rybarczyk", joined=joined)
            form = ProfileForm(instance=profile)
            #because global_tz is Europe/Warsaw values should be localized to this
            form_html = form.as_p()
            self.assertTrue('<input type="hidden" name="joined_2" value="Europe/Warsaw"' in form_html)
        finally:
            global_tz.deactivate()

