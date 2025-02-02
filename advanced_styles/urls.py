from django.urls import path
from .views import fetch_create_style,style_detail

urlpatterns = [
    path('advanced-styles/', fetch_create_style, name='fetch_create_style'),
    path('advanced-styles/<str:style_name>', style_detail, name='style_detail'),
]
