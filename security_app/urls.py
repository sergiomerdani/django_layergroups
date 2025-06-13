from django.urls import path
from .views import geoserver_masterpw,geoserver_self_password,geoserver_acl_layers

urlpatterns = [
    path("security/masterpw",geoserver_masterpw,name="masterpw"),
    path("security/self/password",geoserver_self_password,name="geoserver_self_password"),
    path('security/acl/layers/', geoserver_acl_layers, name='geoserver-acl-layers')
]