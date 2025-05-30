from django.urls import path
from .views import geoserver_users,user_detail

urlpatterns = [
    path("users/",geoserver_users,name="geoserver_users"),
    path("users/<str:username>",user_detail,name="user_detail"),
]
