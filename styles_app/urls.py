from django.urls import path
from .views import GeoStyleView

urlpatterns = [
    path('create-style/', GeoStyleView.as_view(), name='create_style'),
]
