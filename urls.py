from django.conf.urls import url

from . import views

app_name = 'ihr'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    # url(r'^disco/$', views.index_disco, name='disco'),
    url(r'^search/$', views.search, name='search'),
    url(r'^(?P<pk>[0-9]+)/asn/$', views.ASNDetail.as_view(), name='asnDetail'),
    url(r'^(?P<pk>[A-Z]+)/country/$', views.CountryDetail.as_view(), name='countryDetail'),
    url(r'^(?P<pk>[0-9]+)/disco/$', views.DiscoDetail.as_view(), name='discoDetail'),
    url(r'^monitoredAsn/$', views.ASNList.as_view(), name='asnList'),
    url(r'^monitoredCountry/$', views.CountryList.as_view(), name='countryList'),
    url(r'^data/delay/$', views.delayData, name='delayData'),
    url(r'^data/forwarding/$', views.forwardingData, name='forwardingData'),
    url(r'^data/disco/$', views.discoData, name='discoData'),
    url(r'^api/$', views.restful_API, name="root"),
    url(r'^api/delay/$', views.DelayView.as_view(), name='delayListView'),
    url(r'^api/forwarding/$', views.ForwardingView.as_view(), name='forwardingListView'),
    url(r'^api/delay_alarms/$', views.DelayAlarmsView.as_view(), name='delayAlarmsListView'),
    url(r'^api/forwarding_alarms/$', views.ForwardingAlarmsView.as_view(), name='forwardingAlarmsListView'),
    url(r'^api/disco_events/$', views.DiscoEventsView.as_view(), name='discoEventsListView'),
    url(r'^api/disco_probes/$', views.DiscoProbesView.as_view(), name='discoProbesListView'),
]
