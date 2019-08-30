from .const import StrErrors
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework.response import Response
import requests
import json
from django.conf import settings
from rest_framework.views import exception_handler
from rest_framework.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_401_UNAUTHORIZED,
    HTTP_200_OK
)
import logging
logger = logging.getLogger(__name__)
import traceback as tb

def std_response(detail, status_code):
    """
        shortener for error response into views
    """
    return Response({'detail': detail}, status=status_code)


class IHRException(Exception):
    """
    Internal exception. You don't need to catch them they are automatically handled
    """
    def __init__(self, status_code=HTTP_500_INTERNAL_SERVER_ERROR, message=StrErrors.GENERIC, severity=logging.CRITICAL, log=True, traceback=False, *extra):
        #extra arguments will be appendend to message
        self.message = message
        log = log or traceback
        for elem in extra:
            self.message += " " + elem
        super().__init__(self.message)
        if(log):
            logger.log(severity, self.message, tb.format_exc() if traceback else "")
        self.status_code = status_code
        #TODO something more accurate if you want

    def response(self):
        """
        Modify the given response message adding custom fields
        """
        return std_response(self.message, self.status_code)

    # a set of widely used exception
    @staticmethod
    def STD_INVALID(traceback=False):
        return IHRException(status_code=HTTP_401_UNAUTHORIZED, message=StrErrors.INVALID, traceback=traceback)

def IHR_exception_handler(exc, context):
    """
    Exception handler for internal errors
    see the link below for furter details
    https://www.django-rest-framework.org/api-guide/exceptions/
    """
    if isinstance(exc, IHRException):
        return exc.response()

    # default handler
    response = exception_handler(exc, context)

    return response


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (str(user.pk) + user.email + str(user.is_active) + str(timestamp))
    # is active permit automatic token disabling on activation

account_activation_token = TokenGenerator()

class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    def __init__(self, new_email, request_time):
        super().__init__()
        self.new_email = new_email
        self.request_time = request_time

    def _make_hash_value(self, user, timestamp):
        print(str(user.pk), user.email, str(user.is_active), str(timestamp), self.new_email, str(self.request_time))
        return (str(user.pk) + user.email + str(user.is_active) + str(timestamp) + self.new_email + str(self.request_time))


def parse_request(request):
    """
    return the content of the request as a dictionary
    """
    if isinstance(request.data, dict):
        return request.data
    return request.data.dict()

def google_token_verification(request):
    """
    verify the given google recaptcha token.
    """
    try:
        content = json.loads(requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': settings.RECAPTCHA_SECRET,
                'response': request["recaptcha"]
            }
        ).content)
        print(content)
        try:
            if content['success']:
                return True

            if 'invalid-input-response' in content['error-codes']:
                raise IHRException.STD_INVALID()
            if 'timeout-or-duplicate' in content['error-codes']:
                raise IHRException(status_code=HTTP_401_UNAUTHORIZED, message=StrErrors.TRY_AGAIN, log=False)

            raise IHRException(*content['error-codes'], message=StrErrors.RECAPTCHA_MISCONFIGURATION)
        except KeyError as e:
            raise IHRException(str(e), message=StrErrors.RECAPTCHA_MISCONFIGURATION)
    except KeyError as e:
        raise IHRException.STD_INVALID(traceback=True)
    except (ConnectionError, ValueError) as e:
        raise IHRException(str(e), traceback=True)
