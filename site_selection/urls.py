from django.urls import path
from .views import site_selection

urlpatterns = [
    path('site-selection', site_selection, name='site_selection'),
]
