from django.conf import settings
from django.contrib import admin
from django.urls import include, path


handler404 = "news.views.page_not_found"
handler500 = "news.views.server_error"

urlpatterns = [
    path("", include("news.urls")),
]

if settings.ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))
