# -*- coding: utf-8 -*-
import time

from django.conf import settings
from django.contrib import auth
from django.db.models import signals
from django.utils.functional import curry


class AutoLogoutMiddleware(object):
    def process_request(self, request):
        # can't log out if not logged in
        if not request.user.is_authenticated():
            return

        # check if auto logout is activated
        try:
            if not settings.AUTO_LOGOUT_MINUTES:
                return
        except:
            return

        try:
            delta = time.time() - request.session['last_touch']
        except (KeyError, TypeError):
            pass
        else:
            seconds = settings.AUTO_LOGOUT_MINUTES * 60
            if delta > seconds:
                del request.session['last_touch']
                auth.logout(request)
                return

        request.session['last_touch'] = time.time()
