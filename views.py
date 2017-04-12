from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views import generic
from django.core import serializers
from django.db.models import Avg, When, Sum, Case, FloatField

from datetime import datetime, date, timedelta
import pytz
import json

from .models import ASN, Congestion, Forwarding, Congestion_alarms, Forwarding_alarms

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import filters, generics
from .serializers import CongestionSerializer, ForwardingSerializer, CongestionAlarmsSerializer, ForwardingAlarmsSerializer


class CongestionView(generics.ListAPIView): #viewsets.ModelViewSet):
    """
    API endpoint that allows to view the level of congestion.
    """
    queryset = Congestion.objects.all() #.order_by('-asn')
    serializer_class = CongestionSerializer
    filter_backends = (filters.DjangoFilterBackend,filters.OrderingFilter,)
    filter_fields = ('asn', 'timebin',  'magnitude', 'deviation', 'label' ) 
    ordering_fields = ('timebin', 'magnitude', 'deviation')


class ForwardingView(generics.ListAPIView):
    """
    API endpoint that allows to view the level of forwarding anomaly.
    """
    queryset = Forwarding.objects.all()
    serializer_class = ForwardingSerializer
    filter_backends = (filters.DjangoFilterBackend,filters.OrderingFilter,)
    filter_fields = ('asn', 'timebin', 'magnitude', 'resp', 'label')
    ordering_fields = ('timebin', 'magnitude', 'deviation')


class CongestionAlarmsView(generics.ListAPIView): 
    """
    API endpoint that allows to view the congestion alarms.
    """
    queryset = Congestion_alarms.objects.all() #.order_by('-asn')
    serializer_class = CongestionAlarmsSerializer
    filter_backends = (filters.DjangoFilterBackend,filters.OrderingFilter,)
    filter_fields = ('asn', 'timebin',  'link', 'deviation', 'nbprobes' ) 
    ordering_fields = ('timebin', 'deviation', 'nbprobes', 'medianrtt', 'diffmedian')


class ForwardingAlarmsView(generics.ListAPIView):
    """
    API endpoint that allows to view the forwarding alarms.
    """
    queryset = Forwarding_alarms.objects.all()
    serializer_class = ForwardingAlarmsSerializer
    filter_backends = (filters.DjangoFilterBackend,filters.OrderingFilter,)
    filter_fields = ('asn', 'timebin', 'ip', 'previoushop', 'correlation', 'responsibility')
    ordering_fields = ('timebin', 'correlation', 'responsibility')


@api_view(['GET'])
def restful_API(request, format=None):
    """
    API endpoint
    """
    return Response({
        'forwarding': reverse('ihr:forwardingListView', request=request, format=format),
        'congestion': reverse('ihr:congestionListView', request=request, format=format),
        'forwarding_alarms': reverse('ihr:forwardingAlarmsListView', request=request, format=format),
        'congestion_alarms': reverse('ihr:congestionAlarmsListView', request=request, format=format),
    })

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            # return o.isoformat()
            return o.strftime("%Y-%m-%d %H:%M:%S")

        return json.JSONEncoder.default(self, o)

def index(request):
    monitoredAsn = ASN.objects.order_by("number")

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

    tier1 = ASN.objects.filter(number__in = [7018,174,209,3320,3257,286,3356,3549,2914,5511,1239,6453,6762,12956,1299,701,702,703,2828,6461])
    topTier1 = ASN.objects.filter(number__in = [3356, 174, 3257, 1299, 2914])
    rootServers = ASN.objects.filter(number__in = [26415, 2149, 27, 297, 3557, 5927, 13, 29216, 26415, 25152, 20144, 7500, 226])

    ulLen = 5
    if len(monitoredAsn)<15:
        ulLen = 2 #len(monitoredAsn)/3
    
    date = ""
    if "date" in request.GET:
        date = request.GET["date"]

    last = 7
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

def congestionData(request):
    asn = get_object_or_404(ASN, number=request.GET["asn"])

    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]), tzinfo=pytz.utc) 

    last = 7
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 356:
            last = 356

    dtStart = dtEnd - timedelta(last)

    data = Congestion.objects.filter(asn=asn.number, timebin__gte=dtStart,  timebin__lte=dtEnd).order_by("timebin")
    formatedData = {
            "x": list(data.values_list("timebin", flat=True)),
            "y": list(data.values_list("magnitude", flat=True))
            }
    return JsonResponse(formatedData, encoder=DateTimeEncoder) 

def forwardingData(request):
    asn = get_object_or_404(ASN, number=request.GET["asn"])

    dtEnd = datetime.now(pytz.utc)
    if "date" in request.GET and request.GET["date"].count("-") == 2:
        date = request.GET["date"].split("-")
        dtEnd = datetime(int(date[0]), int(date[1]), int(date[2]), tzinfo=pytz.utc) 

    last = 7
    if "last" in request.GET:
        last = int(request.GET["last"])
        if last > 356:
            last = 356

    dtStart = dtEnd - timedelta(last)

    data = Forwarding.objects.filter(asn=asn.number, timebin__gte=dtStart,  timebin__lte=dtEnd).order_by("timebin") 
    formatedData = {
            "x": list(data.values_list("timebin", flat=True)),
            "y": list(data.values_list("magnitude", flat=True))
            }
    return JsonResponse(formatedData, encoder=DateTimeEncoder) 


class ASNDetail(generic.DetailView):
    model = ASN
    
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(ASNDetail, self).get_context_data(**kwargs)

        date = ""
        if "date" in self.request.GET:
            date = self.request.GET["date"]

        last = 7
        if "last" in self.request.GET:
            last = self.request.GET["last"]

        context["date"] = date;
        context["last"] = last;

        return context;

    # template_name = "ihr/asn_detail.html"


class ASNList(generic.ListView):
    model = ASN
    # template_name = "ihr/asn_detail.html"


