from django.contrib.sites.shortcuts import get_current_site
from rest_framework.response import Response
import urllib.parse
import random
import redis
from django.conf import settings as conf_settings
host = conf_settings.REDIS_HOST
print("host => ", host)
POOL = redis.ConnectionPool(host=host, port=6379,max_connections=100, decode_responses=True)
conn = redis.Redis(connection_pool=POOL)

from rest_framework.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_401_UNAUTHORIZED,
    HTTP_200_OK
)

class ConfirmationEmail:
    def __init__(self, email):
        self.email = email
 
    @property
    def creat_code(self, code_num: int = 6):
        base_code = ['0','1','2','3','4','5','6','7','8','9']
        code_list = random.sample(base_code, code_num)
        code = ''.join(code_list)
        return code

    @property
    def PLAIN(self):
        self.code = self.creat_code
        print("self.code:",self.code)
        conn.set(f"Confirmation_{self.email}", self.code, ex=300)
        return f'''
Confirm your email address to get started with Internet Health Report.
Confirmed that {self.email} is your email address to access to the personalization panel.
Confirm email code: {self.code}.
If you haven’t requested this email, you can safely ignore it.'''

class ChangePasswordEmail:
    def __init__(self, email):
        self.email = email
 
    @property
    def creat_code(self, code_num: int = 6):
        base_code = ['0','1','2','3','4','5','6','7','8','9']
        code_list = random.sample(base_code, code_num)
        code = ''.join(code_list)
        return code

    @property
    def PLAIN(self):
        self.code = self.creat_code
        print("self.code:",self.code)
        conn.set(f"ChangePassword_{self.email}", self.code, ex=300)
        return f'''
Confirm your email address to change password.
Confirmed that {self.email} is your email address to access to the personalization panel.
Confirm email code: {self.code}.
If you haven’t requested this email, you can safely ignore it.'''

def std_response(detail, status_code):
    """
        shortener for error response into views
    """
    return Response({'detail': detail}, status=status_code)

class Msg:
    USER_ALREADY_REGISTERED = "User already exists!"
    USER_NOT_EXIST = "User does not exist"
    REGISTER_SUCCEEDED = "User registration succeeded!"
    LOGIN_SUCCEEDED = "User login succeeded!"
    LOGOUT_SUCCEEDED = "User logout succeeded!"
    LOGIN_FAILED = "User login failed, password error!"

    CHANGE_PASSWORD_SUCCEEDED = "User change password succeeded!"

    CODE_ERROR = "Verification code error!"
    CODE_SENT = "Verification code has been sent!"
	
    REQUEST_EXCEPTION = "Request exception!"

    SEARCH_SUCCEEDED = "User search succeeded!"
    SAVE_SUCCEEDED = "User save succeeded!"

    INVALID_DATA = "Invalid data!"
    

class StrErrors:
    OK = "ok"
    GENERIC = "Try again later. If the error persist please contact the administrator"
    WRONG_DATA= "check your data and try again"
    DUPLICATED = "duplicated email"
    INVALID = "invalid"
    TRY_AGAIN = "try again"
    RECAPTCHA_MISCONFIGURATION = "google_token_verification misconfiguration"
    ASN_DOESNOT_EXIST = "one of the as you sent is not in our server"
    ALREADY_VALIDATED = "this user is already validated"
    class INPUT:
        ADD_MONITORING = "you must provide a non empty array of (asn, alertLevel)"
        DUPLICATED = "your input contains duplicated data. Please check and try again"