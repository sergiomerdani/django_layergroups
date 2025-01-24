from django.urls import path
from .views import DrawFeatureAPIView,DeleteFeatureAPIView

urlpatterns = [
    path("add-feature/", DrawFeatureAPIView.as_view(), name="add-feature"),
    path("delete-feature/", DeleteFeatureAPIView.as_view(), name="delete-feature"),
]
