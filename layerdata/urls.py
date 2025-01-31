from django.urls import path
from .views import get_layer_details

urlpatterns = [
    path('<str:layer_name>/', get_layer_details, name='get_layerdata_details'),
]
