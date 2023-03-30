from django.contrib.sites.shortcuts import get_current_site
import urllib.parse
import os


def get_link_domain():
    if os.environ.get("ENV") == "production":
        return "https://ihr.iijlab.net/ihr"
    else:
        return "http://localhost:8080"


class ConfirmationEmail:
    def __init__(self, email, token, password_change=False):
        self.email = email
        self.token = urllib.parse.quote(token)
        self.query = "&active=true" if password_change else ""

    @property
    def PLAIN(self):
        return f'''
Confirm your email address to get started with Internet Health Report

Confirmed that {self.email} is your email address to access to the personalization panel.

Confirm email address
[{get_link_domain()}/en-us/account_activation?token={self.token}{self.query}]

If you haven’t requested this email, you can safely ignore it.
'''

    @property
    def HTML(self):
        return '''HTML VERSION'''


class ResetPasswordEmail:
    def __init__(self, email, token):
        self.email = email
        self.token = urllib.parse.quote(token)

    @property
    def PLAIN(self):
        return f'''
You request a email reset at Internet Health Report

click on the link to reset your password.

[{get_link_domain()}/en-us/reset_password?token={self.token}

If you haven’t requested this email, you can safely ignore it.
'''

    @property
    def HTML(self):
        return '''HTML VERSION'''


class StrErrors:
    OK = "ok"
    GENERIC = "Try again later. If the error persist please contact the administrator"
    WRONG_DATA = "check your data e try again"
    DUPLICATED = "duplicated email"
    INVALID = "invalid"
    TRY_AGAIN = "try again"
    RECAPTCHA_MISCONFIGURATION = "google_token_verification misconfiguration"
    ASN_DOESNOT_EXIST = "one of the as you sent is not in our server"
    ALREADY_VALIDATED = "this user is already validated"

    class INPUT:
        ADD_MONITORING = "you must provide a non empty array of (asn, alertLevel)"
        DUPLICATED = "your input contains duplicated data. Please check and try again"
