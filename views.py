from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, JsonResponse
# from django.core.urlresolvers import reverse
from django.urls import reverse
from django.views import generic
from django.core import serializers
from django.db.models import Avg, When, Sum, Case, FloatField, Count
from django.db import models as django_models

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from django.views.decorators.cache import patch_cache_control, cache_control
from django.utils.decorators import method_decorator
from django.conf import settings as conf_settings
from datetime import datetime, date, timedelta, time, timezone

import pandas as pd
import pytz
import json
import arrow
from email.errors import HeaderParseError
from smtplib import SMTPException
from django.db import transaction, IntegrityError
from django.core.mail import send_mail
from .const import ConfirmationEmail, ChangePasswordEmail, StrErrors, Msg, POOL, std_response
import redis
conn = redis.Redis(connection_pool=POOL)

from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_410_GONE,
    HTTP_409_CONFLICT,
    HTTP_200_OK,
    HTTP_202_ACCEPTED 
)

from .models import ASN, Country, Delay, Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes, Hegemony, HegemonyCone, Atlas_delay, Atlas_location, Atlas_delay_alarms, Hegemony_alarms, Hegemony_country, Hegemony_prefix, Metis_atlas_selection, Metis_atlas_deployment, TR_hegemony

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import generics
from rest_framework.exceptions import ParseError

from .serializers import *
from django_filters import rest_framework as filters
import django_filters
from django.db.models import Q, F

from rest_framework.views import APIView

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import IHRUser, Country, ASN, Atlas_location,IHRUser_Channel
from rest_framework.authtoken.models import Token

# by default shows only one week of data
LAST_DEFAULT = 6
HEGE_GRANULARITY = 15
DEFAULT_MAX_RANGE = 7


########## Get help_text from model ###############
class HelpfulFilterSet(filters.FilterSet):
    @classmethod
    def filter_for_field(cls, f, name, lookup_expr):
        filter = super(HelpfulFilterSet, cls).filter_for_field(f, name, lookup_expr)
        filter.extra['help_text'] = f.help_text
        return filter

########### Custom Pagination ##########
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size_query_param = 'limit'


############ API ##########
def check_timebin(query_params, max_range=DEFAULT_MAX_RANGE):
    """ Check if the query contain timebin parameters"""

    # check if it contains only the timebin field
    timebin = query_params.get('timebin', None)
    if timebin is not None:
        return True

    timebin_gte = query_params.get('timebin__gte', None)
    timebin_lte = query_params.get('timebin__lte', None)

    # check if it contains any of the timebin fields
    if timebin_gte is None and timebin_lte is None:
        raise ParseError("No timebin parameter. Please provide a timebin value or a range of values with timebin__lte and timebin__gte.")

    # check if the range is complete
    if timebin_gte is None or timebin_lte is None:
        raise ParseError("Invalid timebin range. Please provide both timebin__lte and timebin__gte.")

    # check if the range is longer than max_range
    try:
        start = arrow.get(timebin_gte)
        end = arrow.get(timebin_lte)
    except:
        raise ParseError("Could not parse the timebin parameters.")

    if (end-start).days > max_range:
        raise ParseError("The given timebin range is too large. Should be less than {} days.".format(max_range))

    return True

def check_or_fields(query_params, fields):
    """ Check if the query contain any of the given fields"""

    # check if it contains any of the fields
    checks = [query_params.get(f, None) is not None for f in fields]
    if not any(checks):
        raise ParseError("Required parameter missing. Please provide one of the following parameter: {}".format(fields))

    return True

### Filters:
# Generic filter for a list of values:
class ListFilter(django_filters.CharFilter):

    def sanitize(self, value_list):
        """
        remove empty items and parse them
        """
        return [self.customize(v) for v in value_list if v!=""]

    def customize(self, value):
        return value

    def filter(self, qs, value):
        multiple_vals = self.sanitize(value.split(","))
        if len(multiple_vals) > 0:
            par = {self.field_name + "__in": multiple_vals}
            qs = qs.filter(**par)
        return qs

class ListIntegerFilter(ListFilter):

    def customize(self, value):
        return int(value)

class ListStringFilter(ListFilter):

    def filter(self, qs, value):
        multiple_vals = self.sanitize(value.split("|"))
        if len(multiple_vals) > 0:
            par = {self.field_name + "__in": multiple_vals}
            qs = qs.filter(**par)
        return qs

class ListNetworkKeyFilter(ListFilter):

    def filter(self, qs, value):
        queries = None
        multiple_vals = self.sanitize(value.split("|"))

        if len(multiple_vals) > 0:

            first_key = multiple_vals[0]
            queries = Q(
                    **{
                        self.field_name+'__type': first_key[:2], 
                        self.field_name+'__af': int(first_key[2]),
                        self.field_name+'__name': first_key[3:]
                    }) 

            # For each given keys
            for key in multiple_vals[1:]:
                queries |= Q(
                    **{
                        self.field_name+'__type': key[:2], 
                        self.field_name+'__af': int(key[2]),
                        self.field_name+'__name': key[3:]
                    }) 

            qs = qs.filter(queries)

        return qs


class SameASNAndOrigin(django_filters.CharFilter):

    def filter(self, qs, value):

        if value in ['true', 'True', '1']:
            qs = qs.filter(originasn_id=F('asn_id'))

        return qs
    

class NetworkDelayFilter(HelpfulFilterSet):
    startpoint_name = ListStringFilter(field_name='startpoint__name', help_text="Starting location name. It can be a single value or a list of values separated by the pipe character (i.e. | ). The meaning of values dependend on the location type: <ul><li>type=AS: ASN</li><li>type=CT: city name, region name, country code</li><li>type=PB: Atlas Probe ID</li><li>type=IP: IP version (4 or 6)</li></ul> ")
    endpoint_name = ListStringFilter(field_name='endpoint__name', help_text="Ending location name. It can be a single value or a list of values separated by the pipe character (i.e. | ). The meaning of values dependend on the location type: <ul><li>type=AS: ASN</li><li>type=CT: city name, region name, country code</li><li>type=PB: Atlas Probe ID</li><li>type=IP: IP version (4 or 6)</li></ul> ")
    startpoint_type= django_filters.CharFilter(field_name='startpoint__type', help_text="Type of starting location. Possible values are: <ul><li>AS: Autonomous System</li><li>CT: City</li><li>PB: Atlas Probe</li><li>IP: Whole IP space</li></ul>")
    endpoint_type= django_filters.CharFilter(field_name='endpoint__type', help_text="Type of ending location. Possible values are: <ul><li>AS: Autonomous System</li><li>CT: City</li><li>PB: Atlas Probe</li><li>IP: Whole IP space</li></ul>")
    startpoint_af= django_filters.NumberFilter(field_name='startpoint__af', help_text="Address Family (IP version), values are either 4 or 6.")
    endpoint_af= django_filters.NumberFilter(field_name='endpoint__af', help_text="Address Family (IP version), values are either 4 or 6.")

    startpoint_key = ListNetworkKeyFilter(field_name='startpoint', help_text="List of starting location key, separated by the pip character (i.e. | ). A location key is a concatenation of a type, af, and name. For example, CT4New York City, New York, US|AS4174 (yes, the last key corresponds to AS174!).")
    endpoint_key = ListNetworkKeyFilter(field_name='endpoint', help_text="List of ending location key, separated by the pip character (i.e. | ). A location key is a concatenation of a type, af, and name. For example, CT4New York City, New York, US|AS4174 (yes, the last key corresponds to AS174!).")

    class Meta:
        model = Atlas_delay
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'startpoint_name': ['exact'],
            'endpoint_name': ['exact'],
            'startpoint_type': ['exact'],
            'endpoint_type': ['exact'],
            'startpoint_af': ['exact'],
            'endpoint_af': ['exact'],
            'startpoint_key': ['exact'],
            'endpoint_key': ['exact'],
            'median': ['exact', 'lte', 'gte'],
        }
        ordering_fields = ('timebin', 'startpoint_name', 'endpoint_name')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }



class NetworkDelayAlarmsFilter(HelpfulFilterSet):
    startpoint_name = ListStringFilter(field_name='startpoint__name', help_text="Starting location name. It can be a single value or a list of values separated by the pipe character (i.e. | ). The meaning of values dependend on the location type: <ul><li>type=AS: ASN</li><li>type=CT: city name, region name, country code</li><li>type=PB: Atlas Probe ID</li><li>type=IP: IP version (4 or 6)</li></ul> ")
    endpoint_name = ListStringFilter(field_name='endpoint__name', help_text="Ending location name. It can be a single value or a list of values separated by the pipe character (i.e. | ). The meaning of values dependend on the location type: <ul><li>type=AS: ASN</li><li>type=CT: city name, region name, country code</li><li>type=PB: Atlas Probe ID</li><li>type=IP: IP version (4 or 6)</li></ul> ")
    startpoint_type= django_filters.CharFilter(field_name='startpoint__type', help_text="Type of starting location. Possible values are: <ul><li>AS: Autonomous System</li><li>CT: City</li><li>PB: Atlas Probe</li><li>IP: Whole IP space</li></ul>")
    endpoint_type= django_filters.CharFilter(field_name='endpoint__type', help_text="Type of ending location. Possible values are: <ul><li>AS: Autonomous System</li><li>CT: City</li><li>PB: Atlas Probe</li><li>IP: Whole IP space</li></ul>")
    startpoint_af= django_filters.NumberFilter(field_name='startpoint__af', help_text="Address Family (IP version), values are either 4 or 6.")
    endpoint_af= django_filters.NumberFilter(field_name='endpoint__af', help_text="Address Family (IP version), values are either 4 or 6.")

    startpoint_key = ListNetworkKeyFilter(field_name='startpoint', help_text="List of starting location key, separated by the pip character (i.e. | ). A location key is a concatenation of a type, af, and name. For example, CT4New York City, New York, US|AS4174 (yes, the last key corresponds to AS174!).")
    endpoint_key = ListNetworkKeyFilter(field_name='endpoint', help_text="List of ending location key, separated by the pip character (i.e. | ). A location key is a concatenation of a type, af, and name. For example, CT4New York City, New York, US|AS4174 (yes, the last key corresponds to AS174!).")

    class Meta:
        model = Atlas_delay_alarms
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'startpoint_name': ['exact'],
            'endpoint_name': ['exact'],
            'startpoint_type': ['exact'],
            'endpoint_type': ['exact'],
            'startpoint_af': ['exact'],
            'endpoint_af': ['exact'],
            'startpoint_key': ['exact'],
            'endpoint_key': ['exact'],
            'deviation': ['lte', 'gte'],
        }
        ordering_fields = ('timebin', 'startpoint_name', 'endpoint_name')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class HegemonyFilter(HelpfulFilterSet):
    asn = ListIntegerFilter(help_text="Dependency. Transit network commonly seen in BGP paths towards originasn. Can be a single value or a list of comma separated values. ")
    originasn = ListIntegerFilter(help_text="Dependent network, it can be any public ASN. Can be a single value or a list of comma separated values. Retrieve all dependencies of a network by setting a single value and a timebin.")

    class Meta:
        model = Hegemony
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'hege': ['exact', 'lte', 'gte'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'originasn', 'hege', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }


class HegemonyAlarmsFilter(HelpfulFilterSet):
    asn = ListIntegerFilter(help_text="ASN of the anomalous dependency (transit network). Can be a single value or a list of comma separated values.")
    originasn = ListIntegerFilter(help_text="ASN of the reported dependent network. Can be a single value or a list of comma separated values.")

    class Meta:
        model = Hegemony_alarms
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'af': ['exact'],
            'deviation': ['lte', 'gte'],
        }
        ordering_fields = ('timebin', 'originasn', 'deviation', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class HegemonyCountryFilter(HelpfulFilterSet):
    asn = ListIntegerFilter(help_text="Dependency. Network commonly seen in BGP paths towards monitored country. Can be a single value or a list of comma separated values.")
    country = ListFilter(help_text="Monitored country or region (e.g. EU and AP) as defined by its set of ASes registered in registeries delegated files. Can be a single value or a list of comma separated values. Retrieve all dependencies of a country by setting a single value and a timebin.")
    weightscheme = django_filters.CharFilter(help_text="Scheme used to aggregate AS Hegemony scores. 'as' gives equal weight to each AS, 'eyeball' put emphasis on large eyeball networks.")
    transitonly = django_filters.BooleanFilter(help_text="True means that the last AS (origin AS) in BGP paths is ignored, thus focusing only on transit ASes.")

    class Meta:
        model = Hegemony_country
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'hege': ['exact', 'lte', 'gte'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'country', 'hege', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }


class HegemonyPrefixFilter(HelpfulFilterSet):
    prefix = ListFilter(help_text="Monitored prefix, it can be any globally reachable prefix. Can be a single value or a list of comma separated values.")
    originasn = ListIntegerFilter(help_text="Origin network, it can be any public ASN. Can be a single value or a list of comma separated values.")
    asn = ListIntegerFilter(help_text="Dependency. Network commonly seen in BGP paths towards monitored prefix. Can be a single value or a list of comma separated values.")
    country = ListFilter(help_text="Country code for prefixes as reported by Maxmind's Geolite2 geolocation database. Can be a single value or a list of comma separated values. Retrieve all dependencies of a country by setting a single value and a timebin.")
    rpki_status = django_filters.CharFilter(lookup_expr='contains', help_text="Route origin validation state for the monitored prefix and origin AS using RPKI.")
    irr_status = django_filters.CharFilter(lookup_expr='contains', help_text="Route origin validation state for the monitored prefix and origin AS using IRR.")
    delegated_prefix_status = django_filters.CharFilter(lookup_expr='contains', help_text="Status of the monitored prefix in the RIR's delegated stats. Status other than 'assigned' are usually considered as bogons.")
    delegated_asn_status = django_filters.CharFilter(lookup_expr='contains', help_text="Status of the origin ASN in the RIR's delegated stats. Status other than 'assigned' are usually considered as bogons.")
    origin_only = SameASNAndOrigin(help_text="Filter out dependency results and provide only prefix/origin ASN results")

    class Meta:
        model = Hegemony_prefix
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'hege': ['exact', 'lte', 'gte'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'prefix', 'hege', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }


class NetworkDelayLocationsFilter(HelpfulFilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains', help_text="Location identifier, can be searched by substring. The meaning of these values dependend on the location type: <ul><li>type=AS: ASN</li><li>type=CT: city name, region name, country code</li><li>type=PB: Atlas Probe ID</li><li>type=IP: IP version (4 or 6)</li></ul>")
    type = django_filters.CharFilter(help_text="Type of location. Possible values are: <ul><li>AS: Autonomous System</li><li>CT: City</li><li>PB: Atlas Probe</li><li>IP: Whole IP space</li></ul>")
    af = django_filters.NumberFilter(help_text="Address Family (IP version), values are either 4 or 6.")

    class Meta:
        model = Atlas_location
        fields = ["type", "name", "af"]
        ordering_fields = ("name",)

class NetworkFilter(HelpfulFilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains', help_text='Search for a substring in networks name.')
    number = ListIntegerFilter(help_text='Search by ASN or IXP ID. It can be either a single value (e.g. 2497) or a list of comma separated values (e.g. 2497,2500,2501)')
    search = django_filters.CharFilter(method='asn_or_number', help_text='Search for both ASN/IXPID and substring in names.')

    def asn_or_number(self, queryset, name, value):
        if value.startswith("AS") or value.startswith("IX"):
            try:
                tmp = int(value[2:])
                value = value[2:]
            except ValueError:
                pass

        return queryset.filter(
            Q(number__contains=value) | Q(name__icontains=value)
            )

    class Meta:
        model = ASN
        fields = {
                "name": ['exact'],
                "number": ['exact', 'lte', 'gte'],
                }
        ordering_fields = ('number',)

class CountryFilter(HelpfulFilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains', help_text='Search for a substring in countries name.')
    code = django_filters.CharFilter(help_text='Search by country code.')

    class Meta:
        model = Country
        fields = ["name", "code"]
        ordering_fields = ("code",)



class DelayFilter(HelpfulFilterSet):
    """ 
    Explain delay filter here
    """
    asn = ListIntegerFilter(help_text="ASN or IXP ID of the monitored network (see number in /network/). Can be a single value or a list of comma separated values.")
    class Meta:
        model = Delay
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'magnitude': ['exact'],
        }
        ordering_fields = ('timebin', 'magnitude')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class ForwardingFilter(HelpfulFilterSet):
    asn = ListIntegerFilter(help_text="ASN or IXP ID of the monitored network (see number in /network/). Can be a single value or a list of comma separated values.")
    class Meta:
        model = Forwarding
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'magnitude': ['exact'],
        }
        ordering_fields = ('timebin', 'magnitude')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }
class DelayAlarmsFilter(HelpfulFilterSet):
    asn = ListIntegerFilter(help_text="ASN or IXP ID of the monitored network (see number in /network/). Can be a single value or a list of comma separated values.")
    class Meta:
        model = Delay_alarms
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'deviation': ['exact', 'lte', 'gte'],
            'diffmedian': ['exact', 'lte', 'gte'],
            'medianrtt': ['exact', 'lte', 'gte'],
            'nbprobes': ['exact', 'lte', 'gte'],
            'link': ['exact', 'contains'],
        }
        ordering_fields = ('timebin', 'deviation', 'nbprobes', 'diffmedian', 'medianrtt')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class ForwardingAlarmsFilter(HelpfulFilterSet):
    asn = ListIntegerFilter(help_text="ASN or IXP ID of the monitored network (see number in /network/). Can be a single value or a list of comma separated values.")
    class Meta:
        model = Forwarding_alarms
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'correlation': ['exact', 'lte', 'gte'],
            'responsibility': ['exact', 'lte', 'gte'],
            'ip': ['exact', 'contains'],
            'previoushop': ['exact', 'contains'],
        }
        ordering_fields = ('timebin', 'responsibility', 'correlation', 'ip', 'previoushop')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class DiscoEventsFilter(HelpfulFilterSet):
    class Meta:
        model = Disco_events
        fields = {
            'streamname': ['exact'],
            'streamtype': ['exact'],
            'starttime': ['exact', 'lte', 'gte'],
            'endtime': ['exact', 'lte', 'gte'],
            'avglevel': ['exact', 'lte', 'gte'],
            'nbdiscoprobes': ['exact', 'lte', 'gte'],
            'totalprobes': ['exact', 'lte', 'gte'],
            'ongoing': ['exact'],
        }
        ordering_fields = ('starttime', 'endtime', 'avglevel', 'nbdiscoprobes')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }


class HegemonyConeFilter(HelpfulFilterSet):
    asn = ListIntegerFilter(help_text="Autonomous System Number (ASN). Can be a single value or a list of comma separated values.")
    class Meta:
        model = HegemonyCone
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'asn', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class DiscoProbesFilter(HelpfulFilterSet):
    probe_id = ListIntegerFilter(help_text="List of probe ids separated by commas.")
    event = ListIntegerFilter(help_text="List of event ids separated by commas.")
    class Meta:
        model = Disco_probes
        fields = {}
        ordering_fields = ('starttime', 'endtime', 'level')

class UserLoginView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', "password"],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING)
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        print("################")
        try:
            serializer = UserLoginSerializer(data=request.data)
            if serializer.is_valid():
                print("request.data:", request.data)

                email = serializer.validated_data['email']
                password = serializer.validated_data['password']
    
                obj = IHRUser.objects.filter(email=email).first()
                if not obj:
                    ret['code'] = HTTP_202_ACCEPTED
                    ret['msg'] = Msg.USER_NOT_EXIST
                    return JsonResponse(ret, status=HTTP_202_ACCEPTED)
                else:

                    UserModel = get_user_model()
                    user = UserModel.objects.get(email=email)
                    if user.check_password(password):
                        ret['code'] = HTTP_200_OK
                        ret['msg'] = Msg.LOGIN_SUCCEEDED
                        try:
                            token,_ = Token.objects.get_or_create(user=obj)
                            ret['token'] = token.key
                            conn.set(f"Login_{email}", token.key)
                            return JsonResponse(ret, status=HTTP_200_OK)
                        except (KeyError, IHRUser.DoesNotExist)  as e:
                            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
                    else:
                        ret['code'] = HTTP_202_ACCEPTED
                        ret['msg'] = Msg.LOGIN_FAILED
                        return JsonResponse(ret, status=HTTP_202_ACCEPTED)
            else:
                ret['code'] = HTTP_401_UNAUTHORIZED
                ret['msg'] = Msg.INVALID_DATA
                return JsonResponse(ret, status=HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret)


class UserShowView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[]
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        try:
            token = Token.objects.get(key=request.META.get("HTTP_AUTHORIZATION").split('=')[-1])
            user_login = conn.get(f"Login_{token.user}")
            if user_login:
                user = IHRUser.objects.get(email=token.user)
                serializer = UserSerializer(user)
                ret['code'] = HTTP_200_OK
                ret['msg'] = Msg.LOGIN_SUCCEEDED
                ret['data'] = serializer.data
                return JsonResponse(ret, status=HTTP_200_OK)
            else:
                ret['code'] = HTTP_401_UNAUTHORIZED
                ret['msg'] = Msg.LOGIN_FAILED
                return JsonResponse(ret, status=HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret)

class UserLogoutView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[] 
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        try:
            token = Token.objects.get(key=request.META.get("HTTP_AUTHORIZATION").split('=')[-1])
            conn.delete(f"Login_{token.user}")
            user_login = conn.get(f"Login_{token.user}")
            #print(user_login)
            #request.user.auth_token.delete()
            ret['code'] = HTTP_200_OK
            ret['msg'] = Msg.LOGOUT_SUCCEEDED
            return JsonResponse(ret, status=HTTP_202_ACCEPTED)
        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret, status=HTTP_404_NOT_FOUND)

class UserChangePasswordView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', "password", "new_password"],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING)
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        try:
            serializer = UserChangePasswordSerializer(data=request.data)
            
            if serializer.is_valid():
                print("request.data:", request.data)
                email = serializer.validated_data['email']
                password = serializer.validated_data['password']
                new_password = serializer.validated_data['new_password']

                obj = IHRUser.objects.filter(email=email).first()
                if not obj:
                    ret['code'] = HTTP_202_ACCEPTED
                    ret['msg'] = Msg.USER_NOT_EXIST
                    return JsonResponse(ret, status=HTTP_202_ACCEPTED)
                else:
                    UserModel = get_user_model()
                    user = UserModel.objects.get(email=email)
                    if user.check_password(password):
                        ret['code'] = HTTP_200_OK
                        ret['msg'] = Msg.CHANGE_PASSWORD_SUCCEEDED
                        try:
                            obj.password = new_password
                            obj.save()

                            return JsonResponse(ret)
                        except (KeyError, IHRUser.DoesNotExist)  as e:
                            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
                    else:
                        ret['code'] = HTTP_202_ACCEPTED
                        ret['msg'] = Msg.LOGIN_FAILED
                        return JsonResponse(ret, status=HTTP_202_ACCEPTED)
            else:
                ret['code'] = HTTP_400_BAD_REQUEST
                ret['msg'] = Msg.INVALID_DATA
                return JsonResponse(ret, status=HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret)


class UserForgetPasswordView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', "new_password", "code"],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING),
				'code': openapi.Schema(type=openapi.TYPE_STRING)
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        try:
            serializer = UserForgetPasswordSerializer(data=request.data)
            print("request.data:", request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                new_password = serializer.validated_data['new_password']
                code = serializer.validated_data['code']
    
                user_code = conn.get(f"ChangePassword_{email}")
            
                if code == user_code:
                    obj = IHRUser.objects.filter(email=email).first()
                    if obj:
                        obj.set_password(new_password)
                        obj.save()
                        ret['code'] = HTTP_200_OK
                        ret['msg'] = Msg.CHANGE_PASSWORD_SUCCEEDED
                        return JsonResponse(ret, status=HTTP_200_OK)
                    else:
                        ret['code'] = HTTP_202_ACCEPTED
                        ret['msg'] = Msg.USER_NOT_EXIST
                        return JsonResponse(ret, status=HTTP_202_ACCEPTED)
                else:
                    ret['code'] = HTTP_202_ACCEPTED
                    ret['msg'] = Msg.CODE_ERROR
                    return JsonResponse(ret, status=HTTP_202_ACCEPTED)
            else:
                ret['code'] = HTTP_400_BAD_REQUEST
                ret['msg'] = Msg.INVALID_DATA
                return JsonResponse(ret, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret)


class UserRegisterView(APIView):
    queryset = IHRUser.objects.all()
    serializer_class = UserRegisterSerializer
    @swagger_auto_schema(
        
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', "password", "code"],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
				'code': openapi.Schema(type=openapi.TYPE_STRING)
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        try:
            serializer = UserRegisterSerializer(data=request.data)
            print("request.data:", serializer.initial_data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                password = serializer.validated_data['password']
                code = serializer.validated_data['code']
                print("code:", code)

                user_code = conn.get(f"Confirmation_{email}")
                if code == user_code:
                    obj = IHRUser.objects.filter(email=email).first()
                    if obj:
                        ret['code'] = HTTP_200_OK
                        ret['msg'] = Msg.USER_ALREADY_REGISTERED
                        return JsonResponse(ret, status=HTTP_200_OK)
                    else:
                        obj = IHRUser.objects.create_user(email=email, password=password)
                        ret['code'] = HTTP_201_CREATED
                        ret['msg'] = Msg.REGISTER_SUCCEEDED
                        return JsonResponse(ret, status=HTTP_201_CREATED)
                else:

                    ret['code'] = HTTP_400_BAD_REQUEST
                    ret['msg'] = Msg.CODE_ERROR
                    return JsonResponse(ret, status=HTTP_400_BAD_REQUEST)

                    ret['code'] = HTTP_202_ACCEPTED
                    ret['msg'] = Msg.CODE_ERROR
                    return JsonResponse(ret, status=HTTP_202_ACCEPTED)

            else:
                ret['code'] = HTTP_400_BAD_REQUEST
                ret['msg'] = Msg.INVALID_DATA
                return JsonResponse(ret, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret, status=HTTP_404_NOT_FOUND)


class UserSendEmailView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING)
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        
        try:
            serializer = UserEmailSerializer(data=request.data)
            print("request.data:", request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                confirmation_email = ConfirmationEmail(email)

                print(confirmation_email.PLAIN)
                send_mail(
                        'Account activation',
                        confirmation_email.PLAIN,
                        conf_settings.EMAIL_HOST_USER, #TO DO
                        [email],
                        fail_silently=False,
                        )
            else:
                # mohhamedfathyy@gmail.com
                ret['code'] = HTTP_400_BAD_REQUEST
                ret['msg'] = Msg.INVALID_DATA
                return JsonResponse(ret, status=HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return std_response(StrErrors.DUPLICATED, HTTP_409_CONFLICT)
        except (ValueError, SMTPException, HeaderParseError, KeyError) as e:
            print(e)
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
        ret['code'] = HTTP_200_OK
        ret['msg'] = Msg.CODE_SENT
        return JsonResponse(ret, status=HTTP_200_OK)


class UserSendForgetPasswordEmailView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING)
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        
        try:
            serializer = UserEmailSerializer(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data['email']
                confirmation_email = ChangePasswordEmail(email)
                send_mail(
                        'Account activation',
                        confirmation_email.PLAIN,
                        '1347143378@qq.com',
                        [email],
                        fail_silently=False,
                        )
            else:
                ret['code'] = HTTP_400_BAD_REQUEST
                ret['msg'] = Msg.INVALID_DATA
                return JsonResponse(ret, status=HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return std_response(StrErrors.DUPLICATED, HTTP_409_CONFLICT)
        except (ValueError, SMTPException, HeaderParseError, KeyError) as e:
            print(e)
            return std_response(StrErrors.WRONG_DATA, HTTP_400_BAD_REQUEST)
        ret['code'] = HTTP_200_OK
        ret['msg'] = Msg.CODE_SENT
        return JsonResponse(ret, status=HTTP_200_OK)

#  class UserSearchChannelView(APIView):
#     @swagger_auto_schema(
#         operation_description="apiview post description override",
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['type', "content"],
#             properties={
#                 'type': openapi.Schema(type=openapi.TYPE_STRING),
#                 'content': openapi.Schema(type=openapi.TYPE_STRING)
#             },
#         ),
#         security=[]
#     )
#     def post(self, request, *args, **kwargs):
#         ret = {}
#         try:
#             print("request.data:", request.data)
#             type = request.data.get('type')
#             content = request.data.get('content')
#             # Country, ASN, Atlas_location
#             if type == "country":
#                 if content == '':
#                     obj_group = ["Japan", "France", "United States", "Brazil", "Germany", "China", "Singapore", "Canada", "Netherlands", "United Kingdom", "Russia", "Australia"]
#                     ret['code'] = HTTP_200_OK
#                     ret['msg'] = Msg.SEARCH_SUCCEEDED
#                     ret['data'] = obj_group
#                     return JsonResponse(ret)
#                 else:
#                     obj = Country.objects.filter(name__icontains=content)[:30]
#             elif type == "network":
#                 if content == '':
#                     obj_group = ["AS3356 - Lumen", "AS2914 - NTT","AS6939 - HE","AS1299 - Telia","AS174  - Cogent","AS15169 - Google","AS20940 - Akamai","AS16509 - Amazon","AS13335 - Cloudflare","AS32934 - Facebook","AS7922  - Comcast","AS8075  - Microsoft"]
#                     ret['code'] = HTTP_200_OK
#                     ret['msg'] = Msg.SEARCH_SUCCEEDED
#                     ret['data'] = obj_group
#                     return JsonResponse(ret)
#                 else:
#                     obj = ASN.objects.filter(name__icontains=content)[:30]
#             elif type == "city":
#                 if content == '':
#                     obj_group = ["Amsterdam North Holland NL", "Ashburn Virginia US","London England GB","Singapore Central Singapore, SG","Hong Kong Central and Western HK","Frankfurt am Main Hesse DE","Paris Île-de-France FR","Los Angeles California US","Tokyo Tokyo JP","Sydney New South Wales AU","New York City New York US","Toronto Ontario CA"]
#                     ret['msg'] = Msg.SEARCH_SUCCEEDED
#                     ret['data'] = obj_group
#                     return JsonResponse(ret)
#                 else:
#                     obj = Atlas_location.objects.filter(name__icontains=content, type = "CT")[:30]
            
#             obj_group = []
#             for temp in obj:
#                 if type == "city":
#                     obj_group.append(str(temp).replace(",", "")[5:].strip())
#                 else:
#                     obj_group.append(str(temp))
#             print(obj_group)

#             ret['code'] = HTTP_200_OK
#             ret['msg'] = Msg.SEARCH_SUCCEEDED
#             ret['data'] = obj_group
#             return JsonResponse(ret)

#         except Exception as e:
#             print(e)
#             ret['code'] = HTTP_404_NOT_FOUND
#             ret['msg'] = Msg.REQUEST_EXCEPTION
#             return JsonResponse(ret)

# class UserSearchChannelPrefixView(APIView):
#     @swagger_auto_schema(
#         operation_description="apiview post description override",
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=['type', "content"],
#             properties={
#                 'type': openapi.Schema(type=openapi.TYPE_STRING),
#                 'content': openapi.Schema(type=openapi.TYPE_STRING)
#             },
#         ),
#         security=[]
#     )
#     def post(self, request, *args, **kwargs):
#         ret = {}
#         try:
#             print("request.data:", request.data)
#             type = request.data.get('type')
#             content = request.data.get('content')
#             # Country, ASN, Atlas_location
#             if type == "country":
#                 obj = Country.objects.filter(name__icontains=content)[:5]
#             elif type == "network":
#                 obj = ASN.objects.filter(name__icontains=content)[:5]
#             elif type == "city":
#                 obj = Atlas_location.objects.filter(name__icontains=content, type = "CT")[:5]
 
#             obj_group = []
#             for temp in obj:
#                 if type == "city":
#                     for str_temo in str(temp).replace(",", "")[5:].strip().split(" "):
#                         if content in str_temo:
#                             obj_group.append(str_temo)
#                 else:
#                     for str_temo in str(temp).replace(",", "").strip().split(" "):
#                         if content in str_temo:
#                             obj_group.append(str_temo)
#             print(list(set(obj_group)))
#             print(list(set(obj_group))[:5])

#             ret['code'] = HTTP_200_OK
#             ret['msg'] = Msg.SEARCH_SUCCEEDED
#             ret['data'] = list(set(obj_group))[:5]
#             return JsonResponse(ret)

#         except Exception as e:
#             print(e)
#             ret['code'] = HTTP_404_NOT_FOUND
#             ret['msg'] = Msg.REQUEST_EXCEPTION
#             return JsonResponse(ret)


class UserSaveChannelView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['channel'],
            properties={
                'channel': openapi.Schema(type=openapi.TYPE_STRING)
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        try:
            import ast
            print("request.data:", request.data)
            channel = request.data.get('channel')
            print(channel)
            # frequency = request.data.get('channel')
            # print(frequency)
            token = Token.objects.get(key=request.META.get("HTTP_AUTHORIZATION").split('=')[-1])
            # print(len(request.data.get('channel')))

            IHRUser_Channel.objects.filter(name=token.user).delete()
            for temp in range(len(request.data.get('channel'))):
                # print(channel[temp]['channel'])
                # print(channel[temp]['frequency'])
                # print("$$$$$$$$$$")
                obj = IHRUser_Channel.objects.create(channel=channel[temp]['channel'], name=token.user, frequency=channel[temp]['frequency'])
            obj = IHRUser_Channel.objects.filter(name=token.user).first()
            print(obj)
            ret['code'] = HTTP_200_OK
            ret['msg'] = Msg.SAVE_SUCCEEDED
            print(ret)
            return JsonResponse(ret)

        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret)


class UserGetChannelView(APIView):
    @swagger_auto_schema(
        operation_description="apiview post description override",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['type', "content"],
            properties={
                # 'user': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        security=[]
    )
    def post(self, request, *args, **kwargs):
        ret = {}
        try:
            token = Token.objects.get(key=request.META.get("HTTP_AUTHORIZATION").split('=')[-1])
            # print(token.user)
            user_name = token.user # request.data.get('user')
            obj = IHRUser_Channel.objects.filter(name = user_name).values_list('channel','frequency').distinct()

            obj_group = []
            for temp in obj:
                temp_dict = {}
                temp_dict["channel"] = temp[0]
                temp_dict["frequency"] = temp[1]
                obj_group.append(temp_dict)
            # print(obj_group)

            ret['code'] = HTTP_200_OK
            ret['msg'] = Msg.SEARCH_SUCCEEDED
            ret['data'] = {"channel":obj_group}
            return JsonResponse(ret)

        except Exception as e:
            print(e)
            ret['code'] = HTTP_404_NOT_FOUND
            ret['msg'] = Msg.REQUEST_EXCEPTION
            return JsonResponse(ret)

class MetisAtlasSelectionFilter(HelpfulFilterSet):

    class Meta:
        model = Metis_atlas_selection 
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'rank': ['exact', 'lte', 'gte'],
            'metric': ['exact'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'metric', 'rank', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class MetisAtlasDeploymentFilter(HelpfulFilterSet):

    class Meta:
        model = Metis_atlas_deployment 
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'rank': ['exact', 'lte', 'gte'],
            'metric': ['exact'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'metric', 'rank', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }


class TRHegemonyFilter(HelpfulFilterSet):
    origin_name = ListStringFilter(field_name='origin__name', help_text="Origin name. It can be a single value or a list of values separated by the pipe character (i.e. | ). The meaning of values depends on the identifier type: <ul><li>type=AS: ASN</li><li>type=IX: PeeringDB IX ID</li><li>type=MB: IXP member (format: ix_id;asn)</li><li>type=IP: Interface IP of an IXP member</li></ul>")
    dependency_name = ListStringFilter(field_name='dependency__name', help_text="Dependency name. It can be a single value or a list of values separated by the pipe character (i.e. | ). The meaning of values depends on the identifier type: <ul><li>type=AS: ASN</li><li>type=IX: PeeringDB IX ID</li><li>type=MB: IXP member (format: ix_id;asn)</li><li>type=IP: Interface IP of an IXP member</li></ul>")
    origin_type = django_filters.CharFilter(
        field_name='origin__type', help_text="Type of the origin. Possible values are: <ul><li>AS: Autonomous System</li><li>IX: IXP</li><li>MB: IXP member</li><li>IP: IXP member IP</li></ul>")
    dependency_type = django_filters.CharFilter(
        field_name='dependency__type', help_text="Type of the dependency. Possible values are: <ul><li>AS: Autonomous System</li><li>IX: IXP</li><li>MB: IXP member</li><li>IP: IXP member IP</li></ul>")
    origin_af = django_filters.NumberFilter(
        field_name='origin__af', help_text="Address family (IP version) of the origin. Values are either 4 or 6.")
    dependency_af = django_filters.NumberFilter(
        field_name='dependency__af', help_text="Address family (IP version) of the dependency. Values are either 4 or 6.")

    class Meta:
        model = TR_hegemony
        fields = {
            'timebin': ['exact', 'lte', 'gte'],
            'origin_name': ['exact'],
            'dependency_name': ['exact'],
            'origin_type': ['exact'],
            'dependency_type': ['exact'],
            'origin_af': ['exact'],
            'dependency_af': ['exact'],
            'hege': ['exact', 'lte', 'gte'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'origin_name', 'hege', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }


# Views:
cache_1month = [cache_control(max_age=2592000),]

@method_decorator(cache_1month, name='list')
class NetworkView(generics.ListAPIView):
    """
    List networks referenced on IHR (see. /network_delay/locations/ for network delay locations). Can be searched by keyword, ASN, or IXPID.  Range of ASN/IXPID can be obtained with parameters number__lte and number__gte.
    """

    #schema = AutoSchema(tags=['entity'])
    queryset = ASN.objects.all()
    serializer_class = ASNSerializer
    filter_class = NetworkFilter


@method_decorator(cache_1month, name='list')
class CountryView(generics.ListAPIView):
    """
    List countries referenced on IHR. Can be searched by keywordX.
    """

    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    filter_class = CountryFilter

class DelayView(generics.ListAPIView): 
    """
    List cumulated link delay changes (magnitude) for each monitored network.  Magnitude values close to zero represent usual delays for the network, whereas higher values stand for significant links congestion in the monitored network.
    The details of each congested link is available in /delay/alarms/.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """

    serializer_class = DelaySerializer
    filter_class = DelayFilter

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Delay.objects.all()

class ForwardingView(generics.ListAPIView):
    """
    List cumulated forwarding anomaly deviation (magnitude) for each monitored network.  Magnitude values close to zero represent usual forwarding paths for the network, whereas higher positive (resp. negative) values stand for an increasing (resp. decreasing) number of paths passing through the monitored network.
    The details of each forwarding anomaly is available in /forwarding/alarms/.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = ForwardingSerializer
    filter_class = ForwardingFilter

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Forwarding.objects.all()

class DelayAlarmsView(generics.ListAPIView):
    """
    List detected link delay changes.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = DelayAlarmsSerializer
    filter_class = DelayAlarmsFilter

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Delay_alarms.objects.all()

class ForwardingAlarmsView(generics.ListAPIView):
    """
    List anomalous forwarding patterns.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = ForwardingAlarmsSerializer
    filter_class = ForwardingAlarmsFilter

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Forwarding_alarms.objects.all()

class DiscoEventsView(generics.ListAPIView):
    """
    List network disconnections detected with RIPE Atlas. These events have different level of granularity, it can be at a network level (AS), city, or country level.
    """
    queryset = Disco_events.objects.all()
    serializer_class = DiscoEventsSerializer
    filter_class = DiscoEventsFilter

class DiscoProbesView(generics.ListAPIView):
    """
    List details of Atlas probes that triggered network disconnection events.
    """
    queryset = Disco_probes.objects.all() 
    serializer_class = DiscoProbesSerializer
    filter_class = DiscoProbesFilter
    #schema = AutoSchema(tags=['disco'])

class HegemonyView(generics.ListAPIView):
    """
    List AS dependencies for all ASes visible in monitored BGP data. This endpoint also provides the AS dependency to the entire IP space (a.k.a. global graph) which is available by setting the originasn parameter to 0.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = HegemonySerializer
    filter_class = HegemonyFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = date.today()
            past_days = today - timedelta(days=7) 
            if arrow.get(last).date() < past_days: 
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        queryset = Hegemony.objects
        if('timebin' not in self.request.query_params 
                and 'timebin__lte' not in self.request.query_params
                and 'timebin__gte' not in self.request.query_params):
            # Set default timebin value
            today = date.today()
            past_days = today - timedelta(days=LAST_DEFAULT) 
            queryset = queryset.filter(timebin__gte = past_days)
        else:
            check_timebin(self.request.query_params)
        check_or_fields(self.request.query_params, ['originasn', 'asn'])
        return queryset.select_related("originasn", "asn")

class HegemonyAlarmsView(generics.ListAPIView):
    """
    List significant AS dependency changes detected by IHR anomaly detector.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = HegemonyAlarmsSerializer
    filter_class = HegemonyAlarmsFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = date.today()
            past_days = today - timedelta(days=7) 
            if arrow.get(last).date() < past_days: 
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Hegemony_alarms.objects.all()

class HegemonyConeView(generics.ListAPIView):
    """
    The number of networks that depend on a given network. This is similar to CAIDA's customer cone size.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    networks).
    """
    serializer_class = HegemonyConeSerializer
    filter_class = HegemonyConeFilter
    ordering = 'timebin'

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = date.today()
            past_days = today - timedelta(days=7) 
            if arrow.get(last).date() < past_days: 
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return HegemonyCone.objects.all()

class HegemonyCountryView(generics.ListAPIView):
    """
    List AS dependencies of countries. A country infrastructure is defined by its ASes registed in RIRs delegated files. Emphasis can be put on eyeball users with the eyeball weighting scheme (i.e. weightscheme='eyeball').
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 31 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = HegemonyCountrySerializer
    filter_class = HegemonyCountryFilter

    def get_queryset(self):
        queryset = Hegemony_country.objects
        if('timebin' not in self.request.query_params 
                and 'timebin__lte' not in self.request.query_params
                and 'timebin__gte' not in self.request.query_params):
            # Set default timebin value
            today = date.today()
            past_days = today - timedelta(days=LAST_DEFAULT) 
            queryset = queryset.filter(timebin__gte = past_days)
        else:
            check_timebin(self.request.query_params, 31)
        check_or_fields(self.request.query_params, ['country', 'asn'])
        return queryset.select_related("asn")


class HegemonyPrefixView(generics.ListAPIView):
    """
    List AS dependencies of prefixes. 
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte). And one of the following: prefix, originasn, country, rpki_status, irr_status, delegated_prefix_status, delegated_asn_status.</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = HegemonyPrefixSerializer
    filter_class = HegemonyPrefixFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = date.today()
            past_days = today - timedelta(days=7) 
            if arrow.get(last).date() < past_days: 
                patch_cache_control(response, max_age=15552000)
            else:
                max_age = 60*60*6
                patch_cache_control(response, max_age=max_age)

        return response


    def get_queryset(self):
        queryset = Hegemony_prefix.objects
        if('timebin' not in self.request.query_params 
                and 'timebin__lte' not in self.request.query_params
                and 'timebin__gte' not in self.request.query_params):
            # Set default timebin value
            today = date.today()
            past_days = today - timedelta(days=LAST_DEFAULT) 
            queryset = queryset.filter(timebin__gte = past_days)
        else:
            check_timebin(self.request.query_params, 3)
        check_or_fields(self.request.query_params, ['prefix', 'originasn', 'country', 'rpki_status', 'irr_status', 'delegated_prefix_status', 'delegated_asn_status'])
        return queryset.select_related("originasn", "asn")


class NetworkDelayView(generics.ListAPIView):
    """
    List estimated network delays between two potentially remote locations. A location can be, for example, an AS, city, Atlas probe.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = NetworkDelaySerializer
    filter_class = NetworkDelayFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = date.today()
            past_days = today - timedelta(days=7) 
            if arrow.get(last).date() < past_days: 
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Atlas_delay.objects.prefetch_related("startpoint", "endpoint")

class NetworkDelayAlarmsView(generics.ListAPIView):
    """
    List significant network delay changes detected by IHR anomaly detector.
    <ul>
    <li><b>Required parameters:</b> timebin or a range of timebins (using the two parameters timebin__lte and timebin__gte).</li>
    <li><b>Limitations:</b> At most 7 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = NetworkDelayAlarmsSerializer
    filter_class = NetworkDelayAlarmsFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = date.today()
            past_days = today - timedelta(days=7) 
            if arrow.get(last).date() < past_days: 
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Atlas_delay_alarms.objects.prefetch_related("startpoint", "endpoint")

@method_decorator(cache_1month, name='list')
class NetworkDelayLocationsView(generics.ListAPIView):
    """
    List locations monitored for network delay measurements.  A location can be, for example, an AS, city, Atlas probe.
    """
    queryset = Atlas_location.objects.all()
    serializer_class = NetworkDelayLocationsSerializer
    filter_class = NetworkDelayLocationsFilter

class MetisAtlasSelectionView(generics.ListAPIView):
    """
    Metis helps to select a set of diverse Atlas probes in terms of different topological metrics (e.g. AS path, RTT).
    <ul>
    <li><b>Limitations:</b> At most 31 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = MetisAtlasSelectionSerializer
    filter_class = MetisAtlasSelectionFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            past_days = today - timedelta(days=7) 
            if arrow.get(last).datetime < past_days: 
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        queryset = Metis_atlas_selection.objects
        if('timebin' not in self.request.query_params 
                and 'timebin__lte' not in self.request.query_params
                and 'timebin__gte' not in self.request.query_params):
            # Set default timebin value
            today = datetime.combine(date.today(), time.min)
            past_days = today - timedelta(days=6) 
            queryset = queryset.filter(timebin__gte = past_days)
        else:
            check_timebin(self.request.query_params, max_range=31)

        return queryset.select_related("asn")

class MetisAtlasDeploymentView(generics.ListAPIView):
    """
    Metis identifies ASes that are far from Atlas probes. Deploying Atlas probes in these ASes would be beneficial for Atlas coverage.
    <ul>
    <li><b>Limitations:</b> At most 31 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = MetisAtlasDeploymentSerializer
    filter_class = MetisAtlasDeploymentFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin', 
                self.request.query_params.get('timebin__gte', None) )
        if last is not None:
            # Cache forever content that is more than a week old
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            past_days = today - timedelta(days=7) 
            if arrow.get(last).datetime < past_days: 
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        queryset = Metis_atlas_deployment.objects
        if('timebin' not in self.request.query_params 
                and 'timebin__lte' not in self.request.query_params
                and 'timebin__gte' not in self.request.query_params):
            # Set default timebin value
            today = datetime.combine(date.today(), time.min)
            past_days = today - timedelta(days=6) 
            queryset = queryset.filter(timebin__gte = past_days)
        else:
            check_timebin(self.request.query_params, max_range=31)

        return queryset.select_related("asn")


class TRHegemonyView(generics.ListAPIView):
    """
    List AS and IXP dependencies for all ASes visible in monitored traceroute data.
    <ul>
    <li><b>Limitations:</b> At most 31 days of data can be fetched per request. For bulk downloads see: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a>.</li>
    </ul>
    """
    serializer_class = TRHegemonySerializer
    filter_class = TRHegemonyFilter

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        last = self.request.query_params.get('timebin',
                                             self.request.query_params.get('timebin__gte', None))
        if last is not None:
            # Cache forever content that is more than a week old
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            past_days = today - timedelta(days=7)
            if arrow.get(last).datetime < past_days:
                patch_cache_control(response, max_age=15552000)

        return response

    def get_queryset(self):
        queryset = TR_hegemony.objects
        if ('timebin' not in self.request.query_params
                and 'timebin__lte' not in self.request.query_params
                and 'timebin__gte' not in self.request.query_params):
            # Set default timebin value
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            past_days = today - timedelta(days=6)
            queryset = queryset.filter(timebin__gte=past_days)
        else:
            check_timebin(self.request.query_params, max_range=31)
        return TR_hegemony.objects.select_related("origin", "dependency")

# Other pages :


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            # return o.isoformat()
            return o.strftime("%Y-%m-%d %H:%M:%S")

        return json.JSONEncoder.default(self, o)


def index(request):

    # Top congested ASs
    # today = date.today()
    # if "today" in request.GET:
        # part = request.GET["today"].split("-")
        # today = date(int(part[0]), int(part[1]), int(part[2]))
    # limitDate = today-timedelta(days=7)

    # topCongestion = ASN.objects.filter(congestion__timebin__gt=limitDate).annotate(score=Sum("congestion__magnitude")).order_by("-score")[:5]

    # format the end date
    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]), tzinfo=pytz.utc)

    # set the data duration
    last = LAST_DEFAULT
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 356:
            last = 356

    dtStart = dtEnd - timedelta(last)

    # tier1 = ASN.objects.filter(number__in = [7018,174,209,3320,3257,286,3356,3549,2914,5511,1239,6453,6762,12956,1299,701,702,703,2828,6461])
    topTier1 = ASN.objects.filter(number__in = [3356, 174, 3257, 1299, 2914])
    # rootServers = ASN.objects.filter(number__in = [26415, 2149, 27, 297, 3557,
        # 5927, 13, 29216, 26415, 25152, 20144, 7500, 226])
    monitoredAsn = ASN.objects.filter(number__in = [15169, 20940, 7018,209,3320,
        286,3549,5511,1239,6453,6762,12956,701,702,703,2828,6461])
    monitoredCountry = Country.objects.filter(code__in = ["NL","FR","US","IR",
        "ES","DE","JP", "CH", "GB", "IT", "BE", "UA", "PL", "CZ", "CA", "RU",
        "BG","SE","AT","DK","AU","FI","GR","IE","NO","NZ","ZA"])
    nbAsn = (ASN.objects.filter(tartiflette=True)|ASN.objects.filter(disco=True)).count()
    nbCountry = Country.objects.count()

    ulLen = monitoredAsn.count()/2
    ulLen2 = monitoredCountry.count()/2

    date = ""
    if "date" in request.GET:
        date = request.GET["date"]

    last = LAST_DEFAULT
    if "last" in request.GET:
        last = request.GET["last"]

    context = {
            "nbMonitoredAsn": nbAsn-monitoredAsn.count(),
            "nbMonitoredCountry": nbCountry-monitoredCountry.count(),
            "monitoredAsn": monitoredAsn,
            "monitoredCountry": monitoredCountry,
            "topTier1": topTier1 ,
            # "rootServers": rootServers ,
            "date": date,
            "last": last,
            }
    return render(request, "ihr/index.html", context)

def search(request):
    req = request.GET["asn"]
    reqNumber = -1
    try:
        if req.startswith("asn"):
            reqNumber = int(req[3:].partition(" ")[0])
        elif req.startswith("as"):
            reqNumber = int(req[2:].partition(" ")[0])
        else:
            reqNumber = int(req.partition(" ")[0])
    except ValueError:
        return HttpResponseRedirect(reverse("ihr:index"))

    asn = get_object_or_404(ASN, number=reqNumber)
    return HttpResponseRedirect(reverse("ihr:asnDetail", args=(asn.number,)))

def delayData(request):
    asn = get_object_or_404(ASN, number=request.GET["asn"])

    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]),23,59, tzinfo=pytz.utc)

    last = LAST_DEFAULT
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 356:
            last = 356

    dtStart = dtEnd - timedelta(last)

    data = Delay.objects.filter(asn=asn.number, timebin__gte=dtStart,  timebin__lte=dtEnd).order_by("timebin")
    formatedData = {"AS"+str(asn.number): {
            "x": list(data.values_list("timebin", flat=True)),
            "y": list(data.values_list("magnitude", flat=True))
            }}
    return JsonResponse(formatedData, encoder=DateTimeEncoder)

def forwardingData(request):
    asn = get_object_or_404(ASN, number=request.GET["asn"])

    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]),23,59, tzinfo=pytz.utc)

    last = LAST_DEFAULT
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 356:
            last = 356

    dtStart = dtEnd - timedelta(last)

    data = Forwarding.objects.filter(asn=asn.number, timebin__gte=dtStart,  timebin__lte=dtEnd).order_by("timebin")
    formatedData ={"AS"+str(asn.number): {
            "x": list(data.values_list("timebin", flat=True)),
            "y": list(data.values_list("magnitude", flat=True))
            }}
    return JsonResponse(formatedData, encoder=DateTimeEncoder)


def eventToStepGraph(dtStart, dtEnd, stime, etime, lvl, eventid):
    """Convert a disco event to a list of x, y ,eventid values for the step
    graph.
    """

    x = [dtStart]
    y = ["0"]
    ei = ["0"]

    # change the first value if there is an event starting before dtStart
    if len(stime) and min(stime) < dtStart:
        idx = stime.index(min(stime))
        y[0] = lvl[idx]
        ei[0] = eventid[idx]
        x.append(etime[idx])
        x.append(etime[idx])
        y.append(y[0])
        y.append("0")
        ei.append(ei[0])
        ei.append("0")

        stime.pop(idx)
        etime.pop(idx)
        lvl.pop(idx)
        eventid.pop(idx)

    for s, e, l, i in zip(stime,etime,lvl,eventid):
        x.append(s)
        x.append(s)
        x.append(e)
        x.append(e)
        y.append("0")
        y.append(l)
        y.append(l)
        y.append("0")
        ei.append("0")
        ei.append(i)
        ei.append(i)
        ei.append("0")

    if x[-1] < dtEnd:
        x.append(dtEnd)
        y.append("0")
        ei.append("0")

    return x, y, ei


def discoGeoData(request):
    # format the end date
    minLevel=8
    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]), 23, 59, tzinfo=pytz.utc)

    # set the data duration
    last = LAST_DEFAULT
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 356:
            last = 356

    dtStart = dtEnd - timedelta(last)

    # find corresponding ASN or country
    streams = Disco_events.objects.filter(endtime__gte=dtStart,
        starttime__lte=dtEnd,avglevel__gte=minLevel).exclude(streamtype='asn').distinct("streamname").values("streamname", "starttime",  "avglevel", "id")

    formatedData = {}
    for stream in streams:
        eventid = stream["id"]

        probeData = Disco_probes.objects.filter(event=eventid ).values("lat", "lon")
        # eventid=list(data.values_list("id", flat=True))

        for probe in probeData:
            formatedData[stream["streamname"]] = {
                "lvl": stream["avglevel"],
                "dtStart": stream["starttime"],
                "eventid": eventid,
                "lat": probe["lat"],
                "lon": probe["lon"],
                }
            # plotting requires only one probe
            break

    return JsonResponse(formatedData, encoder=DateTimeEncoder)

def discoData(request):
    # format the end date
    minLevel = 8 
    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]), 23, 59, tzinfo=pytz.utc)

    # set the data duration
    last = LAST_DEFAULT
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 365:
            last = 365

    dtStart = dtEnd - timedelta(last)

    # find corresponding ASN or country
    if "asn" in request.GET:
        asn = get_object_or_404(ASN, number=request.GET["asn"])
        streams= [{"streamtype":"asn", "streamname": asn.number}]
    elif "cc" in request.GET:
        country = get_object_or_404(Country, code=request.GET["cc"])
        streams= [{"streamtype":"country", "streamname": country.code}]
    else:
        streams = Disco_events.objects.filter(endtime__gte=dtStart,
            starttime__lte=dtEnd,avglevel__gte=minLevel).exclude(streamtype="admin1").exclude(streamtype='admin2').exclude(streamname="All").distinct("streamname").values("streamname", "streamtype")

    formatedData = {}
    for stream in streams:
        streamtype = stream["streamtype"]
        streamname = stream["streamname"]

        data = Disco_events.objects.filter(streamtype=streamtype, streamname=streamname,
                endtime__gte=dtStart,  starttime__lte=dtEnd,avglevel__gte=minLevel).order_by("starttime")
        stime = list(data.values_list("starttime", flat=True))
        etime = list(data.values_list("endtime", flat=True))
        lvl =   list(data.values_list("avglevel", flat=True))
        eventid=list(data.values_list("id", flat=True))

        x, y ,ei = eventToStepGraph(dtStart, dtEnd, stime, etime, lvl, eventid)

        df = pd.DataFrame({"lvl": y, "eid": ei}, index=x)
        prefix = "CC" if streamtype=="country" else "AS"
        formatedData[prefix+str(streamname)] = {
                "streamtype": streamtype,
                "streamname": streamname,
                "dtStart": dtStart,
                "dtEnd": dtEnd,
                "stime": stime,
                "etime": etime,
                "rawx": x,
                "rawy": y,
                "rawe": ei,
                "x": list(df.index.to_pydatetime()),
                "y": list(df["lvl"].values),
                "eventid": list(df["eid"].values),
                }

    return JsonResponse(formatedData, encoder=DateTimeEncoder)


def hegemonyData(request):
    asn = get_object_or_404(ASN, number=request.GET["originasn"])
    af=4
    if "af" in request.GET and request.GET["af"] in ["4","6"]:
        af=request.GET["af"]

    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]),23,59, tzinfo=pytz.utc)

    last = LAST_DEFAULT
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 365:
            last = 365

    dtStart = dtEnd - timedelta(last)

    rawData = Hegemony.objects.filter(originasn=asn.number, af=af, timebin__gte=dtStart,  timebin__lte=dtEnd, hege__gte=0.0001).order_by("timebin")
    cache = list(rawData)
    formatedData = {}
    allAsn = set()
    seenAsn = set()
    currentTimebin = None
    for row in cache:
        a = row.asn_id
        if a==asn.number:
            continue

        if currentTimebin is None:
            currentTimebin = row.timebin

        if currentTimebin != row.timebin :
            while currentTimebin+timedelta(minutes=HEGE_GRANULARITY/2) < row.timebin :
                for a0 in allAsn.difference(seenAsn):
                    formatedData["AS"+str(a0)]["x"].append(currentTimebin)
                    formatedData["AS"+str(a0)]["y"].append(0)
                # currentTimebin = row.timebin
                currentTimebin += timedelta(minutes=HEGE_GRANULARITY)
                seenAsn = set()

        seenAsn.add(a)
        if "AS"+str(a) not in formatedData:
            formatedData["AS"+str(a)] = {"x":[], "y":[]}
            allAsn.add(a)
        formatedData["AS"+str(a)]["x"].append(row.timebin)
        formatedData["AS"+str(a)]["y"].append(row.hege)

    return JsonResponse(formatedData, encoder=DateTimeEncoder)

def coneData(request):
    asn = get_object_or_404(ASN, number=request.GET["asn"])
    af=4
    if "af" in request.GET and request.GET["af"] in ["4","6"]:
        af=request.GET["af"]

    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]),23,59, tzinfo=pytz.utc)

    last = LAST_DEFAULT
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 356:
            last = 356

    dtStart = dtEnd - timedelta(last)

    data = HegemonyCone.objects.filter(asn=asn.number, af=af, timebin__gte=dtStart,  timebin__lte=dtEnd).order_by("timebin")
    # data = Hegemony.objects.filter(asn=asn.number, af=af, timebin__gte=dtStart,  timebin__lte=dtEnd).exclude(originasn=0).exclude(originasn=asn.number).values("timebin").annotate(nb_asn=Count("originasn", distinct=True)).order_by("timebin")

    formatedData ={"AS"+str(asn.number): {
            "x": list(data.values_list("timebin", flat=True)),
            "y": list(data.values_list("conesize", flat=True))
            }}

    return JsonResponse(formatedData, encoder=DateTimeEncoder)


# def discoData(request):
    # if "asn" in request.GET:
        # streamtype = "asn"
        # asn = get_object_or_404(ASN, number=request.GET["asn"])
        # streamname = asn.number
    # elif "cc" in request.GET:
        # streamtype= "country"
        # country = get_object_or_404(Country, code=request.GET["cc"])
        # streamname = country.code

    # dtEnd = datetime.now(pytz.utc)
    # if "date" in request.GET and request.GET["date"].count("-") == 2:
        # date = request.GET["date"].split("-")
        # dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]), tzinfo=pytz.utc)

    # last = 30
    # if "last" in request.GET:
        # last = int(request.GET["last"])
        # if last > 356:
            # last = 356

    # dtStart = dtEnd - timedelta(last)

    # data = Disco_events.objects.filter(streamtype=streamtype, streamname=streamname,
            # endtime__gte=dtStart,  starttime__lte=dtEnd).order_by("starttime")
    # stime = list(data.values_list("starttime", flat=True))
    # etime = list(data.values_list("endtime", flat=True))
    # lvl =   list(data.values_list("avglevel", flat=True))
    # eventid=list(data.values_list("id", flat=True))
    # x = []
    # y = []
    # ei = []
    # for s, e, l, i in zip(stime,etime,lvl,eventid):
        # x.append(s)
        # x.append(e)
        # y.append(l)
        # y.append(l)
        # ei.append(i)
        # ei.append(i)

    # formatedData = {
            # "x": x,
            # "y": y,
            # "eventid": ei,
            # }
    # return JsonResponse(formatedData, encoder=DateTimeEncoder)



class ASNDetail(generic.DetailView):
    model = ASN

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ASNDetail, self).get_context_data(**kwargs)

        date = ""
        if "date" in self.request.GET:
            date = self.request.GET["date"]

        last = LAST_DEFAULT
        if "last" in self.request.GET:
            last = self.request.GET["last"]

        af = 4
        if "af" in self.request.GET:
            af = self.request.GET["af"]

        context["date"] = date;
        context["last"] = last;
        context["af"] = int(af);
        context["ashashValidDate"] = (date == "" or datetime.strptime(date,"%Y-%m-%d")>datetime(2018,1,15))

        return context;

    # template_name = "ihr/asn_detail.html"



class CountryDetail(generic.DetailView):
    model = Country

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(CountryDetail, self).get_context_data(**kwargs)

        date = ""
        if "date" in self.request.GET:
            date = self.request.GET["date"]

        last = LAST_DEFAULT
        if "last" in self.request.GET:
            last = self.request.GET["last"]

        context["date"] = date;
        context["last"] = last;

        return context;



class ASNList(generic.ListView):
    # model = ASN
    queryset = ASN.objects.filter(tartiflette=True) | ASN.objects.filter(disco=True)
    ordering = ["number"]


class CountryList(generic.ListView):
    model = Country
    ordering = ["name"]
