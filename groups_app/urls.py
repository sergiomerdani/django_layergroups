from django.urls import path
from .views import geoserver_groups, geoserver_group_detail

urlpatterns = [
    path("usergroups/",geoserver_groups,name="geoserver_groups"),
    path("usergroups/<str:groupname>/",geoserver_group_detail,name="geoserver_group_detail"),
]

