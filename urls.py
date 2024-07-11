from django.conf.urls import url
from django.views.generic import TemplateView

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


from . import views
#from .user_api import urls as user_urls

#from rest_framework_swagger.views import get_swagger_view
#schema_view = get_swagger_view(title='API')
from drf_yasg.generators import OpenAPISchemaGenerator


exposed_api = [
    # User webpage not yet integrated 
    #url(r'^user/sendregisteremail$', views.UserSendEmailView.as_view(), name='UserSendEmailListView'),
    #url(r'^user/sendforgetpasswordemail$', views.UserSendForgetPasswordEmailView.as_view(), name='UserSendForgetPasswordEmailListView'),
    #url(r'^user/register$', views.UserRegisterView.as_view(), name='UserRegisterListView'),
#	url(r'^user/login$', views.UserLoginView.as_view(), name='UserLoginListView'),
#	url(r'^user/logout$', views.UserLogoutView.as_view(), name='UserLogoutListView'),
#    url(r'^user/changepassword$', views.UserChangePasswordView.as_view(), name='UserChangePasswordListView'),
#	url(r'^user/forgetpassword$', views.UserForgetPasswordView.as_view(), name='UserForgetPasswordListView'),

#	url(r'^user/savechannel$', views.UserSaveChannelView.as_view(), name='UserSaveChannelListView'),
#	url(r'^user/getchannel$', views.UserGetChannelView.as_view(), name='UserGetChannelListView'),

    url(r'^ihr/api/networks/$', views.NetworkView.as_view(), name='networkListView'),
    url(r'^ihr/api/countries/$', views.CountryView.as_view(), name='countryListView'),
    url(r'^ihr/api/link/delay/$', views.DelayView.as_view(), name='delayListView'),
    url(r'^ihr/api/link/forwarding/$', views.ForwardingView.as_view(), name='forwardingListView'),
    url(r'^ihr/api/link/delay/alarms/$', views.DelayAlarmsView.as_view(), name='delayAlarmsListView'),
    url(r'^ihr/api/link/forwarding/alarms/$', views.ForwardingAlarmsView.as_view(), name='forwardingAlarmsListView'),
    url(r'^ihr/api/disco/events/$', views.DiscoEventsView.as_view(), name='discoEventsListView'),
    url(r'^ihr/api/hegemony/$', views.HegemonyView.as_view(), name='hegemonyListView'),
    url(r'^ihr/api/hegemony/alarms/$', views.HegemonyAlarmsView.as_view(), name='hegemonyAlarmsListView'),
    url(r'^ihr/api/hegemony/countries/$', views.HegemonyCountryView.as_view(), name='hegemonyCountryListView'),
    url(r'^ihr/api/hegemony/prefixes/$', views.HegemonyPrefixView.as_view(), name='hegemonyPrefixListView'),
    url(r'^ihr/api/hegemony/cones/$', views.HegemonyConeView.as_view(), name='hegemonyConeListView'),
    url(r'^ihr/api/network_delay/$', views.NetworkDelayView.as_view(), name='networkDelayListView'),
    url(r'^ihr/api/network_delay/locations/$', views.NetworkDelayLocationsView.as_view(), name='networkDelayLocationsListView'),
    url(r'^ihr/api/network_delay/alarms/$', views.NetworkDelayAlarmsView.as_view(), name='networkDelayAlarmsListView'),
    url(r'^ihr/api/metis/atlas/selection/$', views.MetisAtlasSelectionView.as_view(), name='metisAtlasSelectionListView'),
    url(r'^ihr/api/metis/atlas/deployment/$', views.MetisAtlasDeploymentView.as_view(), name='metisAtlasDeploymentListView'),
    url(r'^ihr/api/tr_hegemony/$', views.TRHegemonyView.as_view(), name='trHegemonyListView'),
]

schema_view = get_schema_view(
       openapi.Info(
         title="IHR API",
         default_version='',
         description="""This RESTful API is intended for developers and researchers integrating IHR data to their workflow. API data is also available via our <a href='/ihr/en-us/documentation#Python_Library'>Python library</a>.
         <b>For bulk downloads please use: <a href="https://ihr-archive.iijlab.net/" target="_blank">https://ihr-archive.iijlab.net/</a></b>
         <br>Parameters ending with __lte and __gte (acronyms for 'less than or equal to', and, 'greater than or equal to') are used for selecting a range of values.""",
         # terms_of_service="https://ihr.iijlab.net/ihr/en-us/documentation#Data_policy",
         contact=openapi.Contact(email="admin@ihr.live"),
         license=openapi.License(name="Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)",
         url="https://creativecommons.org/licenses/by-nc-sa/4.0/"),
      ),
      public=True,
      permission_classes=(permissions.AllowAny,),
      patterns=exposed_api,
 )

app_name = 'ihr'
urlpatterns = [
    url(r'^ihr/api/swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # refered in the base.html template
        # User webpage not yet integrated 
    #*user_urls.urlpatterns
] + exposed_api
