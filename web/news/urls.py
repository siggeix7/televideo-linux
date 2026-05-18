from django.urls import path

from . import views


app_name = "news"

urlpatterns = [
    path("", views.home, name="home"),
    path("superenalotto/", views.superenalotto, name="superenalotto"),
    path("healthz/", views.healthcheck, name="healthcheck"),
    path("api/news/", views.news_api, name="news_api"),
    path("api/superenalotto/", views.superenalotto_api, name="superenalotto_api"),
]
