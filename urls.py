from django.conf.urls import url

from . import views

app_name = 'ihr'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^search/$', views.search, name='search'),
    url(r'^(?P<pk>[0-9]+)/asn/$', views.ASNDetail.as_view(), name='asnDetail'),
    url(r'^monitoredAsn/$', views.ASNList.as_view(), name='asnList'),
    url(r'^data/congestion/$', views.congestionData, name='congestionData'),
    url(r'^data/forwarding/$', views.forwardingData, name='forwardingData'),
    url(r'^api/$', views.restful_API, name="root"),
    url(r'^api/congestion/$', views.CongestionView.as_view(), name='congestionListView'),
    url(r'^api/forwarding/$', views.ForwardingView.as_view(), name='forwardingListView'),
    url(r'^api/congestion_alarms/$', views.CongestionAlarmsView.as_view(), name='congestionAlarmsListView'),
    url(r'^api/forwarding_alarms/$', views.ForwardingAlarmsView.as_view(), name='forwardingAlarmsListView'),
]
