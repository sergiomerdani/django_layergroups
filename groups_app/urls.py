from django.urls import path
from .views import geoserver_groups, geoserver_group_detail,geoserver_roles_for_group

urlpatterns = [
    path("usergroups/",geoserver_groups,name="geoserver_groups"),
    path("usergroups/<str:groupname>/",geoserver_group_detail,name="geoserver_group_detail"),
    path("usergroups/<str:groupname>/roles",    geoserver_roles_for_group),
]

