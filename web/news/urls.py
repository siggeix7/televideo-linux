from django.urls import path

from . import views


app_name = "news"

urlpatterns = [
    path("", views.home, name="home"),
    path("api/news/", views.news_api, name="news_api"),
]
