from django.urls import path
from .views import geoserver_masterpw,geoserver_self_password

urlpatterns = [
    path("security/masterpw",geoserver_masterpw,name="masterpw"),
    path("security/self/password",geoserver_self_password,name="geoserver_self_password"),
]