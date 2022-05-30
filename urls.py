from django.conf.urls import url
from django.views.generic import TemplateView

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


from . import views
from .user_api import urls as user_urls

#from rest_framework_swagger.views import get_swagger_view
#schema_view = get_swagger_view(title='API')
from drf_yasg.generators import OpenAPISchemaGenerator


exposed_api = [ 
    url(r'^networks/$', views.NetworkView.as_view(), name='networkListView'),
    url(r'^countries/$', views.CountryView.as_view(), name='countryListView'),
    url(r'^link/delay/$', views.DelayView.as_view(), name='delayListView'),
    url(r'^link/forwarding/$', views.ForwardingView.as_view(), name='forwardingListView'),
    url(r'^link/delay/alarms/$', views.DelayAlarmsView.as_view(), name='delayAlarmsListView'),
    url(r'^link/forwarding/alarms/$', views.ForwardingAlarmsView.as_view(), name='forwardingAlarmsListView'),
    url(r'^disco/events/$', views.DiscoEventsView.as_view(), name='discoEventsListView'),
    url(r'^hegemony/$', views.HegemonyView.as_view(), name='hegemonyListView'),
    url(r'^hegemony/alarms/$', views.HegemonyAlarmsView.as_view(), name='hegemonyAlarmsListView'),
    url(r'^hegemony/countries/$', views.HegemonyCountryView.as_view(), name='hegemonyCountryListView'),
    url(r'^hegemony/prefixes/$', views.HegemonyPrefixView.as_view(), name='hegemonyPrefixListView'),
    url(r'^hegemony/cones/$', views.HegemonyConeView.as_view(), name='hegemonyConeListView'),
    url(r'^network_delay/$', views.NetworkDelayView.as_view(), name='networkDelayListView'),
    url(r'^network_delay/locations/$', views.NetworkDelayLocationsView.as_view(), name='networkDelayLocationsListView'),
    url(r'^network_delay/alarms/$', views.NetworkDelayAlarmsView.as_view(), name='networkDelayAlarmsListView'),
    url(r'^metis/atlas/selection/$', views.MetisAtlasSelectionView.as_view(), name='metisListView'),
]   

schema_view = get_schema_view(
       openapi.Info(
         title="IHR API",
         default_version='',
         description="""This RESTful API is intended for developpers and researchers who want to fetch Internet Health Report data and integrate IHR results to their workflow. IHR data is also available via our <a href='/ihr/en-us/documentation#Python_Library'>Python library</a>. 
         <br>Parameters ending with __lte and __gte (acronyms for 'less than or equal to', and, 'greater than or equal to') are used for selecting a range of values.""",
         # terms_of_service="https://ihr.iijlab.net/ihr/en-us/documentation#Data_policy",
         contact=openapi.Contact(email="ihr-admin@iij-ii.co.jp"),
         license=openapi.License(name="Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)",
         url="https://creativecommons.org/licenses/by-nc-sa/4.0/"),
      ),
      public=True,
      permission_classes=(permissions.AllowAny,),
      patterns=exposed_api,
 )

app_name = 'ihr'
urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # refered in the base.html template
    url(r'^$', views.index, name='index'),
    url(r'^search/$', views.search, name='search'),
    url(r'^monitoredAsn/$', views.ASNList.as_view(), name='asnList'),
    url(r'^monitoredCountry/$', views.CountryList.as_view(), name='countryList'),

    # to remove?
    #url(r'^$', TemplateView.as_view(template_name='index.html')),
    # url(r'^disco/$', views.index_disco, name='disco'),
    #url(r'^(?P<pk>-?[0-9]+)/asn/$', views.ASNDetail.as_view(), name='asnDetail'),
    #url(r'^(?P<pk>[A-Z]+)/country/$', views.CountryDetail.as_view(), name='countryDetail'),
    #url(r'^(?P<pk>[0-9]+)/disco/$', views.DiscoDetail.as_view(), name='discoDetail'),
    # TODO remove /data/ endpoints
    #url(r'^data/delay/$', views.delayData, name='delayData'),
    #url(r'^data/forwarding/$', views.forwardingData, name='forwardingData'),
    #url(r'^data/disco/$', views.discoData, name='discoData'),
    #url(r'^data/geodisco/$', views.discoGeoData, name='discoGeoData'),
    #url(r'^data/hegemony/$', views.hegemonyData, name='hegemonyData'),
    #url(r'^data/hegemonyCone/$', views.coneData, name='coneData'),
    #url(r'^api/$', views.restful_API, name="root"),

    # old API endpoints
    url(r'^delay_alarms/$', views.DelayAlarmsView.as_view(), name='delayAlarmsListView'),
    url(r'^forwarding_alarms/$', views.ForwardingAlarmsView.as_view(), name='forwardingAlarmsListView'),
    url(r'^disco_events/$', views.DiscoEventsView.as_view(), name='discoEventsListView'),
    url(r'^disco_probes/$', views.DiscoProbesView.as_view(), name='discoProbesListView'),
    url(r'^hegemony_alarms/$', views.HegemonyAlarmsView.as_view(), name='hegemonyAlarmsListView'),
    url(r'^hegemony_cone/$', views.HegemonyConeView.as_view(), name='hegemonyConeListView'),
    url(r'^network_delay_locations/$', views.NetworkDelayLocationsView.as_view(), name='networkDelayLocationsListView'),
    url(r'^network_delay_alarms/$', views.NetworkDelayAlarmsView.as_view(), name='networkDelayAlarmsListView'),
    *user_urls.urlpatterns
] + exposed_api
