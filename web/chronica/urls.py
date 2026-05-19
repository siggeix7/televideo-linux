from django.conf import settings
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("news.urls")),
]

if settings.ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))
