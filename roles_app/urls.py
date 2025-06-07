from django.urls import path
from .views import geoserver_roles, geoserver_role_detail

urlpatterns = [
    path("roles/", geoserver_roles, name="geoserver_roles"),
    path("roles/<str:rolename>/", geoserver_role_detail, name="geoserver_role_detail")    
]
