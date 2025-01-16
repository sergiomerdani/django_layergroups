from django.urls import path
from .views import layer_list,layer_detail

urlpatterns = [
    path('<str:workspace>/<str:datastore>/', layer_list, name='datastore-layers'),
    path('<str:workspace>/<str:datastore>/<str:layer_name>/', layer_detail, name='layer-detail'),
]
