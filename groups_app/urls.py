from django.urls import path
from .views import geoserver_groups, geoserver_group_detail

urlpatterns = [
    path("groups/",geoserver_groups,name="geoserver_groups"),
    path("groups/<str:groupname>/",geoserver_group_detail,name="geoserver_group_detail"),
]
