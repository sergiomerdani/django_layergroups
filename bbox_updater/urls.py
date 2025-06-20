from django.urls import path
from .views import update_bbox

urlpatterns = [
    path('update-bbox/<str:layer_name>/', update_bbox, name='update-bbox')
]
