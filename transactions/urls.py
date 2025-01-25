from django.urls import path
from .views import DrawFeatureAPIView,DeleteFeatureAPIView,ModifyFeatureAPIView, UpdateFeatureAttributesAPIView

urlpatterns = [
    path("add-feature/", DrawFeatureAPIView.as_view(), name="add-feature"),
    path("delete-feature/", DeleteFeatureAPIView.as_view(), name="delete-feature"),
    path("modify-feature/", ModifyFeatureAPIView.as_view(), name="modify-feature"),
    path("update-feature-attributes/", UpdateFeatureAttributesAPIView.as_view(), name="update-feature-attributes"),
]
