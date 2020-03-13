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

from datetime import datetime, date, timedelta
import pandas as pd
import pytz
import json
import arrow

from .models import ASN, Country, Delay, Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes, Hegemony, HegemonyCone, Atlas_delay, Atlas_location, Atlas_delay_alarms, Hegemony_alarms

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import generics
from rest_framework.exceptions import ParseError

from .serializers import ASNSerializer, CountrySerializer, DelaySerializer, ForwardingSerializer, DelayAlarmsSerializer, ForwardingAlarmsSerializer, DiscoEventsSerializer, DiscoProbesSerializer, HegemonySerializer, HegemonyConeSerializer, NetworkDelaySerializer, NetworkDelayLocationsSerializer, NetworkDelayAlarmsSerializer, HegemonyAlarmsSerializer
from django_filters import rest_framework as filters
import django_filters
from django.db.models import Q



# by default shows only one week of data
LAST_DEFAULT = 7
HEGE_GRANULARITY = 15
MAX_RANGE = 7


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
def check_timebin(query_params):
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

    # check if the range is longer than MAX_RANGE
    try:
        start = arrow.get(timebin_gte)
        end = arrow.get(timebin_lte)
    except:
        raise ParseError("Could not parse the timebin parameters.")

    if (end-start).days > MAX_RANGE:
        raise ParseError("The given timebin range is too large. Should be less than {} days.".format(MAX_RANGE))

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

class NetworkDelayFilter(HelpfulFilterSet):
    startpoint_name = ListStringFilter(field_name='startpoint__name')
    endpoint_name = ListStringFilter(field_name='endpoint__name')
    startpoint_type= django_filters.CharFilter(field_name='startpoint__type')
    endpoint_type= django_filters.CharFilter(field_name='endpoint__type')
    startpoint_af= django_filters.NumberFilter(field_name='startpoint__af')
    endpoint_af= django_filters.NumberFilter(field_name='endpoint__af')

    startpoint_key = ListNetworkKeyFilter(field_name='startpoint')
    endpoint_key = ListNetworkKeyFilter(field_name='endpoint')

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
        }
        ordering_fields = ('timebin', 'startpoint_name', 'endpoint_name')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }



class NetworkDelayAlarmsFilter(HelpfulFilterSet):
    startpoint_name = ListStringFilter(field_name='startpoint__name')
    endpoint_name = ListStringFilter(field_name='endpoint__name')
    startpoint_type= django_filters.CharFilter(field_name='startpoint__type')
    endpoint_type= django_filters.CharFilter(field_name='endpoint__type')
    startpoint_af= django_filters.NumberFilter(field_name='startpoint__af')
    endpoint_af= django_filters.NumberFilter(field_name='endpoint__af')

    startpoint_key = ListNetworkKeyFilter(field_name='startpoint')
    endpoint_key = ListNetworkKeyFilter(field_name='endpoint')

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
    asn = ListIntegerFilter()
    originasn = ListIntegerFilter()

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
    asn = ListIntegerFilter()
    originasn = ListIntegerFilter()

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

class NetworkDelayLocationsFilter(HelpfulFilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    type = django_filters.CharFilter()
    af = django_filters.NumberFilter()

    class Meta:
        model = Atlas_location
        fields = ["type", "name", "af"]
        ordering_fields = ("name",)

class NetworkFilter(HelpfulFilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains', help_text='Search for a substring in networks name.')
    number = ListIntegerFilter(help_text='Search by ASN or IXP ID. It can be either a single value (e.g. 2497) or a list of values (e.g. 2497,2500,2501)')
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
        ordering_fields = ("number",)



class DelayFilter(HelpfulFilterSet):
    """ 
    Explain delay filter here
    """
    asn = ListIntegerFilter(help_text="Filter by ASN")
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
    asn = ListIntegerFilter()
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
    asn = ListIntegerFilter()
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
    asn = ListIntegerFilter()
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
    asn = ListIntegerFilter()
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
    probe_id = ListIntegerFilter()
    event = ListIntegerFilter()
    class Meta:
        model = Disco_probes
        fields = {}
        ordering_fields = ('starttime', 'endtime', 'level')



###################### Views:
class NetworkView(generics.ListAPIView):
    """
    List networks referenced on IHR (see. /network_delay/locations/ for network 
    delay locations). Can be searched by keyword, ASN, or IXPID.  Range of 
    ASN/IXPID can be obtained with parameters number__lte and number__gte.
    """
    #schema = AutoSchema(tags=['entity'])
    queryset = ASN.objects.all()
    serializer_class = ASNSerializer
    filter_class = NetworkFilter

class CountryView(generics.ListAPIView):
    """
    List countries referenced on IHR. Can be searched by keyword, ASN, or IXPID. 
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    filter_class = CountryFilter

class DelayView(generics.ListAPIView): 
    f"""
    List cumulated link delay changes (magnitude) for each monitored network. 
    Magnitude values close to zero represent usual delays for the network, 
    whereas higher values stand for significant links congestion in the 
    monitored network.
    The details of each congested link is available in /delay/alarms/.
    <br>
    <b>Required parameters:</b> timebin or a range of timebins (using
    the two parameters timebin__lte and timebin__gte).
    <b>Limitations:</b> At most {MAX_RANGE} days of data can be fetch per 
    request.
    """
    serializer_class = DelaySerializer
    filter_class = DelayFilter

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Delay.objects.all()

class ForwardingView(generics.ListAPIView):
    f"""
    List cumulated forwarding anomaly deviation (magnitude) for each monitored 
    network.  Magnitude values close to zero represent usual forwarding paths
    for the network, whereas higher positive (resp. negative) values stand for 
    an increasing (resp. decreasing) number of paths passing through the 
    monitored 
    network.
    The details of each forwarding anomaly is available in /forwarding/alarms/.
    <br>
    <b>Required parameters:</b> timebin or a range of timebins (using
    the two parameters timebin__lte and timebin__gte).
    <b>Limitations:</b> At most {MAX_RANGE} days of data can be fetch per 
    request.
    """
    serializer_class = ForwardingSerializer
    filter_class = ForwardingFilter
    #schema = AutoSchema(tags=['link'])

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Forwarding.objects.all()

class DelayAlarmsView(generics.ListAPIView):
    """
    API endpoint that allows to view the delay alarms.
    """
    serializer_class = DelayAlarmsSerializer
    filter_class = DelayAlarmsFilter
    #schema = AutoSchema(tags=['link'])

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Delay_alarms.objects.all()

class ForwardingAlarmsView(generics.ListAPIView):
    """
    API endpoint that allows to view the forwarding alarms.
    """
    serializer_class = ForwardingAlarmsSerializer
    filter_class = ForwardingAlarmsFilter
    #schema = AutoSchema(tags=['link'])

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Forwarding_alarms.objects.all()

class DiscoEventsView(generics.ListAPIView):
    """
    API endpoint that allows to view the events reported by disco.
    """
    queryset = Disco_events.objects.all()
    serializer_class = DiscoEventsSerializer
    filter_class = DiscoEventsFilter
    #schema = AutoSchema(tags=['disco'])

class DiscoProbesView(generics.ListAPIView):
    """
    API endpoint that allows to view disconnected probes.
    """
    probe_id = ListIntegerFilter()

    queryset = Disco_probes.objects.all() 
    serializer_class = DiscoProbesSerializer
    filter_class = DiscoProbesFilter
    #schema = AutoSchema(tags=['disco'])

class HegemonyView(generics.ListAPIView):
    """
    API endpoint that allows to view AS hegemony scores.
    """
    serializer_class = HegemonySerializer
    filter_class = HegemonyFilter
    ordering = 'timebin'

    def get_queryset(self):
        check_timebin(self.request.query_params)
        check_or_fields(self.request.query_params, ['originasn', 'asn'])
        return Hegemony.objects.all()

class HegemonyAlarmsView(generics.ListAPIView):
    """
    API endpoint that allows to view AS hegemony scores.
    """
    serializer_class = HegemonyAlarmsSerializer
    filter_class = HegemonyAlarmsFilter

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Hegemony_alarms.objects.all()

class HegemonyConeView(generics.ListAPIView):
    """
    API endpoint that allows to view AS hegemony cones (number of dependent
    networks).
    """
    serializer_class = HegemonyConeSerializer
    filter_class = HegemonyConeFilter
    ordering = 'timebin'

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return HegemonyCone.objects.all()

class NetworkDelayView(generics.ListAPIView):
    """
    API endpoint that allows to view network delay between diverse locations.
    """
    serializer_class = NetworkDelaySerializer
    filter_class = NetworkDelayFilter
    ordering = 'timebin'

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Atlas_delay.objects.all()

class NetworkDelayAlarmsView(generics.ListAPIView):
    """
    API endpoint that allows to view detected network delay alarms.
    """
    serializer_class = NetworkDelayAlarmsSerializer
    filter_class = NetworkDelayAlarmsFilter

    def get_queryset(self):
        check_timebin(self.request.query_params)
        return Atlas_delay_alarms.objects.all()

class NetworkDelayLocationsView(generics.ListAPIView):
    """
    API endpoint for network locations found in Atlas traceroutes
    """
    queryset = Atlas_location.objects.all()
    serializer_class = NetworkDelayLocationsSerializer
    filter_class = NetworkDelayLocationsFilter

###### Other pages :

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


class DiscoDetail(generic.DetailView):
    model = Disco_events

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(DiscoDetail, self).get_context_data(**kwargs)

        return context;

    template_name = "ihr/disco_detail.html"
