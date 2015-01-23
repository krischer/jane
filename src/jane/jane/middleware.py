# -*- coding: utf-8 -*-
import time

from django.conf import settings
from django.contrib import auth
from django.db.models import signals
from django.utils.functional import curry


class WhoDidItMiddleware(object):
    """
    Add user created_by and modified_by foreign key to any model automatically.
    Almost entirely taken from https://github.com/Atomidata/django-audit-log/
    """
    def process_request(self, request):
        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            if hasattr(request, 'user') and request.user.is_authenticated():
                user = request.user
            else:
                user = None
            mark_whodid = curry(self.mark_whodid, user)
            signals.pre_save.connect(mark_whodid,
                                     dispatch_uid=(self.__class__, request,),
                                     weak=False)

    def process_response(self, request, response):
        signals.pre_save.disconnect(dispatch_uid=(self.__class__, request,))
        return response

    def mark_whodid(self, user, sender, instance, **kwargs):  # @UnusedVariable
        if not getattr(instance, 'created_by_id', None):
            instance.created_by = user
        if hasattr(instance, 'modified_by_id'):
            instance.modified_by = user


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
