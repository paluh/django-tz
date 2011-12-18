# -*- coding:utf-8 -*-
from django.conf import settings
from django.http import HttpResponseRedirect

from .forms import TimeZoneForm

def set_timezone(request):
    """
    Nearly 1:1 copy of django.views.i18n.set_language, but it sets timezone not language.
    """

    next = request.REQUEST.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
    if not next:
        next = '/'
    response = HttpResponseRedirect(next)
    if request.method == 'POST':
        form = TimeZoneForm(request.POST)
        if form.is_valid():
            if hasattr(request, 'session'):
                session_name = getattr(settings, 'TIMEZONE_SESSION_NAME', 'django_timezone')
                request.session[session_name] = form.cleaned_data['timezone']
            else:
                cookie_name = getattr(settings, 'TIMEZONE_COOKIE_NAME', 'TIMEZONE')
                response.set_cookie(cookie_name, form.cleaned_data['timezone'])
    return response
