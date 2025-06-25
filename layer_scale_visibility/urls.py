from django.urls import path
from .views import layer_list_api,style_detail_api

urlpatterns = [
    path('scale-visibility/', layer_list_api, name='visibility'),
    path('scale-visibility/<str:style_name>/', style_detail_api, name='style_detail'),
]
