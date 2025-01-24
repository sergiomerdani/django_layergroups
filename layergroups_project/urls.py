from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("layergroups.urls")),
    path("api/", include("layers.urls")),
    path("api/", include("table_api.urls")),
    path("styles/", include("styles_app.urls")),
    path("api/", include("transactions.urls")),
]
