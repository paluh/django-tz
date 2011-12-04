# -*- coding:utf-8 -*-
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^settz/$', 'django_tz.views.set_timezone',
            name='django_tz_set_timezone'),
)
