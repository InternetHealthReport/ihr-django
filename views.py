from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from django.views import generic
from django.core import serializers
from django.db.models import Avg, When, Sum, Case, FloatField

from datetime import datetime, date, timedelta
import json

from .models import ASN, Congestion, Forwarding

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import filters, generics
from .serializers import CongestionSerializer, ForwardingSerializer


class CongestionView(generics.ListAPIView): #viewsets.ModelViewSet):
    """
    API endpoint that allows to view the level of congestion.
    """
    queryset = Congestion.objects.all() #.order_by('-asn')
    serializer_class = CongestionSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('asn', 'timebin',  'magnitude', 'deviation', 'label' ) 


class ForwardingView(generics.ListAPIView):
    """
    API endpoint that allows to view the level of forwarding anomaly.
    """
    queryset = Forwarding.objects.all()
    serializer_class = ForwardingSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('asn', 'timebin', 'magnitude', 'resp', 'label')


@api_view(['GET'])
def restful_API(request, format=None):
    """
    API endpoint
    """
    return Response({
        'forwarding': reverse('ihr:forwardingListView', request=request, format=format),
        'congestion': reverse('ihr:congestionListView', request=request, format=format),
    })

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            # return o.isoformat()
            return o.strftime("%Y-%m-%d %H:%M:%S")

        return json.JSONEncoder.default(self, o)

def index(request):
    monitoredAsn = ASN.objects.order_by("number")

    today = date.today()
    if "today" in request.GET:
        part = request.GET["today"].split("-")
        today = date(int(part[0]), int(part[1]), int(part[2]))
    limitDate = today-timedelta(days=7)
    print(limitDate)
    # TODO remove the following line (used only with test data)
    limitDate = datetime(2015,1,1)

    topCongestion = ASN.objects.filter(congestion__timebin__gt=limitDate).annotate(score=Sum("congestion__magnitude")).order_by("-score")[:5]

    print(topCongestion)
    ulLen = 5
    if len(monitoredAsn)<15:
        ulLen = 2 #len(monitoredAsn)/3

    context = {"monitoredAsn0": monitoredAsn[:ulLen], "monitoredAsn1": monitoredAsn[ulLen:ulLen*2],
            "monitoredAsn2": monitoredAsn[ulLen*2:ulLen*3],"nbMonitoredAsn": len(monitoredAsn)-ulLen*3,
            "topCongestion": topCongestion }
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
    data = Congestion.objects.filter(asn=asn.number)
    formatedData = {
            "x": list(data.values_list("timebin", flat=True)),
            "y": list(data.values_list("magnitude", flat=True))
            }
    return JsonResponse(formatedData, encoder=DateTimeEncoder) 

def forwardingData(request):
    asn = get_object_or_404(ASN, number=request.GET["asn"])
    data = Forwarding.objects.filter(asn=asn.number) 
    formatedData = {
            "x": list(data.values_list("timebin", flat=True)),
            "y": list(data.values_list("magnitude", flat=True))
            }
    return JsonResponse(formatedData, encoder=DateTimeEncoder) 


class ASNDetail(generic.DetailView):
    model = ASN
    # template_name = "ihr/asn_detail.html"


class ASNList(generic.ListView):
    model = ASN
    # template_name = "ihr/asn_detail.html"


