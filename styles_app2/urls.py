from django.urls import path
from .views import styles_list_create_view, style_detail_view

urlpatterns = [
    path('', styles_list_create_view, name='styles_list_create'),
    path('<str:style_name>/', style_detail_view, name='style_detail'),
]
