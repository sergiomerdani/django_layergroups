from django.urls import path
from .views import DrawFeatureAPIView

urlpatterns = [
    path("add-feature/", DrawFeatureAPIView.as_view(), name="add-feature"),
]
