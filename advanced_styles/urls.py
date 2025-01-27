from django.urls import path
from .views import create_style

urlpatterns = [
    path('create-style/', create_style, name='create_style'),
]
