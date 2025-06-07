from django.urls import path
from .views import geoserver_users,user_detail,user_groups,geoserver_roles_for_user

urlpatterns = [
    path("users/",geoserver_users,name="geoserver_users"),
    path("users/<str:username>",user_detail,name="user_detail"),
    path('users/<str:username>/groups/', user_groups, name='user_groups'),
    path('users/<str:username>/roles/', geoserver_roles_for_user, name='geoserver_roles_for_user'),
]
