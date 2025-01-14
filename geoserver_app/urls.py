from django.urls import path
from .views import layergroup_list, layergroup_detail

urlpatterns = [
    path("api/layergroups/", layergroup_list, name="layergroup-list"),
    path("api/layergroups/<str:name>/", layergroup_detail, name="layergroup-detail"),
]
