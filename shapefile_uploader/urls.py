from django.urls import path
from .views import upload_shapefile

urlpatterns = [
    path('upload-shapefile/', upload_shapefile, name='upload_shapefile'),
]