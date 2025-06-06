from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("layergroups.urls")),
    path("api/", include("layers.urls")),
    path("api/", include("table_api.urls")),
    path("styles/", include("styles_app.urls")),
    path("api/", include("transactions.urls")),
    path("api/", include("advanced_styles.urls")),
    path("layerdata/", include("layerdata.urls")),
    path("api/", include("users_app.urls")),
    path("api/", include("users_app.urls")),
    path("api/", include("groups_app.urls")),
    path("api/", include("roles_app.urls")),
]