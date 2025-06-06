from django.urls import path
from .views import geoserver_users,user_detail,user_groups

urlpatterns = [
    path("users/",geoserver_users,name="geoserver_users"),
    path("users/<str:username>",user_detail,name="user_detail"),
    path('users/<str:username>/groups/', user_groups, name='user_groups'),
]
