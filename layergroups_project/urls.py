from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("geoserver/", include("geoserver_app.urls")),
    path("layers/", include("layers.urls")),
]
