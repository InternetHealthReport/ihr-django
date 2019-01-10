from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
# from django.core.urlresolvers import reverse
from django.urls import reverse
from django.views import generic
from django.core import serializers
from django.db.models import Avg, When, Sum, Case, FloatField, Count
from django.db import models as django_models

from datetime import datetime, date, timedelta
import pytz
import json
import pandas as pd

from .models import ASN, Country, Delay, Forwarding, Delay_alarms, Forwarding_alarms, Disco_events, Disco_probes, Hegemony, HegemonyCone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import generics
from .serializers import ASNSerializer, DelaySerializer, ForwardingSerializer, DelayAlarmsSerializer, ForwardingAlarmsSerializer, DiscoEventsSerializer, DiscoProbesSerializer, HegemonySerializer, HegemonyConeSerializer
from django_filters import rest_framework as filters 
import django_filters
from django.db.models import Q

# by default shows only one week of data
LAST_DEFAULT = 7

HEGE_GRANULARITY = 15

########### Custom Pagination ##########
from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size_query_param = 'limit'

############ API ##########

### Filters:
# Generic filter for a list of values:
class ListFilter(django_filters.CharFilter):

    def sanitize(self, value_list):
        """
        remove empty items in case of ?number=1,,2
        """
        return [v for v in value_list if v != u'']

    def customize(self, value):
        return value

    def filter(self, qs, value):
        multiple_vals = value.split(u",")
        multiple_vals = self.sanitize(multiple_vals)
        multiple_vals = map(self.customize, multiple_vals)
        actual_filter = django_filters.fields.Lookup(multiple_vals, 'in')
        return super(ListFilter, self).filter(qs, actual_filter)

class ListIntegerFilter(ListFilter):

    def customize(self, value):
        return int(value)

class HegemonyFilter(filters.FilterSet):
    asn = ListIntegerFilter()
    originasn = ListIntegerFilter()

    class Meta:
        model = Hegemony
        fields = {
            'originasn': ['exact'],
            'asn': ['exact'],
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

class ASNFilter(filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    number = django_filters.NumberFilter()
    search = django_filters.CharFilter(method='asn_or_number')

    def asn_or_number(self, queryset, name, value):
        return queryset.filter(
            Q(number__contains=value) | Q(name__icontains=value)
            )

    class Meta:
        model = ASN
        fields = ["name", "number"]
        ordering_fields = ('number',)


class DelayFilter(filters.FilterSet):
    class Meta:
        model = Delay
        fields = {
            'asn': ['exact'],
            'timebin': ['exact', 'lte', 'gte'],
            'magnitude': ['exact'],
        }
        ordering_fields = ('timebin', 'magnitude')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }

class ForwardingFilter(filters.FilterSet):
    class Meta:
        model = Forwarding
        fields = {
            'asn': ['exact'],
            'timebin': ['exact', 'lte', 'gte'],
            'magnitude': ['exact'],
        }
        ordering_fields = ('timebin', 'magnitude')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }
class DelayAlarmsFilter(filters.FilterSet):
    class Meta:
        model = Delay_alarms
        fields = {
            'asn': ['exact'],
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

class ForwardingAlarmsFilter(filters.FilterSet):
    class Meta:
        model = Forwarding_alarms
        fields = {
            'asn': ['exact'],
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

class DiscoEventsFilter(filters.FilterSet):
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


class HegemonyConeFilter(filters.FilterSet):
    class Meta:
        model = HegemonyCone
        fields = {
            'asn': ['exact'],
            'timebin': ['exact', 'lte', 'gte'],
            'af': ['exact'],
        }
        ordering_fields = ('timebin', 'asn', 'af')

    filter_overrides = {
        django_models.DateTimeField: {
            'filter_class': filters.IsoDateTimeFilter
        },
    }


### Views:
class ASNView(generics.ListAPIView):
    """
    API endpoint that allows to view/search AS and IX
    """
    queryset = ASN.objects.all()
    serializer_class = ASNSerializer
    filter_class = ASNFilter

class DelayView(generics.ListAPIView): #viewsets.ModelViewSet):
    """
    API endpoint that allows to view the level of congestion.
    """
    queryset = Delay.objects.all()
    serializer_class = DelaySerializer
    filter_class = DelayFilter


class ForwardingView(generics.ListAPIView):
    """
    API endpoint that allows to view the level of forwarding anomaly.
    """
    queryset = Forwarding.objects.all()
    serializer_class = ForwardingSerializer
    filter_class = ForwardingFilter


class DelayAlarmsView(generics.ListAPIView): 
    """
    API endpoint that allows to view the delay alarms.
    """
    queryset = Delay_alarms.objects.all() #.order_by('-asn')
    serializer_class = DelayAlarmsSerializer
    filter_class = DelayAlarmsFilter


class ForwardingAlarmsView(generics.ListAPIView):
    """
    API endpoint that allows to view the forwarding alarms.
    """
    queryset = Forwarding_alarms.objects.all()
    serializer_class = ForwardingAlarmsSerializer
    filter_class = ForwardingAlarmsFilter

class DiscoEventsView(generics.ListAPIView):
    """
    API endpoint that allows to view the events reported by disco.
    """
    queryset = Disco_events.objects.all()
    serializer_class = DiscoEventsSerializer
    filter_class = DiscoEventsFilter

class DiscoProbesView(generics.ListAPIView): 
    """
    API endpoint that allows to view disconnected probes.
    """
    queryset = Disco_probes.objects.all() #.order_by('-asn')
    serializer_class = DiscoProbesSerializer
    filter_fields = ('probe_id', 'event' ) 
    ordering_fields = ('starttime', 'endtime', 'level')


class HegemonyView(generics.ListAPIView):
    """
    API endpoint that allows to view AS hegemony scores.
    """
    queryset = Hegemony.objects.all().order_by("timebin")
    serializer_class = HegemonySerializer
    filter_class = HegemonyFilter


class HegemonyConeView(generics.ListAPIView):
    """
    API endpoint that allows to view AS hegemony cones (number of dependent
    networks).
    """
    queryset = HegemonyCone.objects.all().order_by("timebin")
    serializer_class = HegemonyConeSerializer
    filter_class = HegemonyConeFilter



@api_view(['GET'])
def restful_API(request, format=None):
    """
    API endpoint
    """
    return Response({
        'forwarding': reverse('ihr:forwardingListView', request=request, format=format),
        'delay': reverse('ihr:delayListView', request=request, format=format),
        'forwarding_alarms': reverse('ihr:forwardingAlarmsListView', request=request, format=format),
        'delay_alarms': reverse('ihr:delayAlarmsListView', request=request, format=format),
        'disco_events': reverse('ihr:discoEventsListView', request=request, format=format),
        'disco_probes': reverse('ihr:discoProbesListView', request=request, format=format),
        'hegemony': reverse('ihr:hegemonyListView', request=request, format=format),
        'hegemony_cone': reverse('ihr:hegemonyConeListView', request=request, format=format),
    })


###### Other pages :

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            # return o.isoformat()
            return o.strftime("%Y-%m-%d %H:%M:%S")

        return json.JSONEncoder.default(self, o)

def index_old(request):

    # Top congested ASs
    # today = date.today()
    # if "today" in request.GET:
        # part = request.GET["today"].split("-")
        # today = date(int(part[0]), int(part[1]), int(part[2]))
    # limitDate = today-timedelta(days=7)
    # print(limitDate)
    # # TODO remove the following line (used only with test data)
    # limitDate = datetime(2015,1,1)

    # topCongestion = ASN.objects.filter(congestion__timebin__gt=limitDate).annotate(score=Sum("congestion__magnitude")).order_by("-score")[:5]

    # tier1 = ASN.objects.filter(number__in = [7018,174,209,3320,3257,286,3356,3549,2914,5511,1239,6453,6762,12956,1299,701,702,703,2828,6461])
    topTier1 = ASN.objects.filter(number__in = [3356, 174, 3257, 1299, 2914])
    rootServers = ASN.objects.filter(number__in = [26415, 2149, 27, 297, 3557, 5927, 13, 29216, 26415, 25152, 20144, 7500, 226])
    monitoredAsn = ASN.objects.order_by("number")

    ulLen = 5
    if len(monitoredAsn)<15:
        ulLen = 2 #len(monitoredAsn)/3
    
    date = ""
    if "date" in request.GET:
        date = request.GET["date"]

    last = LAST_DEFAULT
    if "last" in request.GET:
        last = request.GET["last"]

    context = {"monitoredAsn0": monitoredAsn[1:ulLen+1], "monitoredAsn1": monitoredAsn[ulLen+1:1+ulLen*2],
            "monitoredAsn2": monitoredAsn[1+ulLen*2:1+ulLen*3],"monitoredAsn3": monitoredAsn[1+ulLen*3:1+ulLen*4],
            "nbMonitoredAsn": len(monitoredAsn)-ulLen*4,
            "topTier1": topTier1 ,
            "rootServers": rootServers ,
            "date": date,
            "last": last,
            }
    return render(request, "ihr/index.html", context)

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
    minLevel=12
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
        starttime__lte=dtEnd,avglevel__gte=minLevel, streamtype="geo").distinct("streamname").values("streamname", "starttime",  "avglevel", "id")
        
    formatedData = {}
    for stream in streams:
        eventid = stream["id"]

        probeData = Disco_probes.objects.filter(event=eventid, probe_id=int(stream["streamname"].partition("-")[2])).values("lat", "lon")
        # eventid=list(data.values_list("id", flat=True))

        for probe in probeData:
            formatedData[stream["streamname"]] = {
                "lvl": stream["avglevel"],
                "dtStart": stream["starttime"],
                "eventid": eventid,
                "lat": probe["lat"],
                "lon": probe["lon"],
                }

    return JsonResponse(formatedData, encoder=DateTimeEncoder) 

def discoData(request):
    # format the end date
    minLevel = 12
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
    if "asn" in request.GET:
        asn = get_object_or_404(ASN, number=request.GET["asn"])
        streams= [{"streamtype":"asn", "streamname": asn.number}]
    elif "cc" in request.GET:
        country = get_object_or_404(Country, code=request.GET["cc"])
        streams= [{"streamtype":"country", "streamname": country.code}]
    else:
        streams = Disco_events.objects.filter(endtime__gte=dtStart,
            starttime__lte=dtEnd,avglevel__gte=minLevel).exclude(streamtype="geo").exclude(streamname="All").distinct("streamname").values("streamname", "streamtype")
        
    formatedData = {}
    for stream in streams:
        streamtype = stream["streamtype"]
        streamname = stream["streamname"]

        data = Disco_events.objects.filter(streamtype=streamtype, streamname=streamname, 
                endtime__gte=dtStart,  starttime__lte=dtEnd,avglevel__gte=10).order_by("starttime") 
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
        if last > 356:
            last = 356

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
