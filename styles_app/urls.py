from django.urls import path
from .views import GeoStyleView

urlpatterns = [
    path('allstyles/', GeoStyleView.as_view(), name='create_style'),
]
