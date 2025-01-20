from django.urls import path
from .views import manage_columns

urlpatterns = [
    path("columns/", manage_columns, name="manage_columns"),
]
