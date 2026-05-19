from django.urls import path

from . import views


app_name = "news"

urlpatterns = [
    path("", views.home, name="home"),
    path("tv/", views.tv, name="tv"),
    path("cultura/", views.culture, name="culture"),
    path("cultura/", views.culture, name="cultura"),
    path("ambiente/", views.environment, name="environment"),
    path("ambiente/", views.environment, name="ambiente"),
    path("lavoro/", views.work, name="work"),
    path("lavoro/", views.work, name="lavoro"),
    path("sport/", views.sport, name="sport"),
    path("meteo/", views.weather, name="weather"),
    path("meteo/", views.weather, name="meteo"),
    path("viaggi/", views.travel, name="travel"),
    path("viaggi/", views.travel, name="viaggi"),
    path("giochi/", views.games, name="games"),
    path("giochi/", views.games, name="giochi"),
    path("regioni/", views.regions, name="regions"),
    path("regioni/<slug:region_slug_value>/", views.regions, name="region"),
    path("superenalotto/", views.superenalotto, name="superenalotto"),
    path("healthz/", views.healthcheck, name="healthcheck"),
    path("api/news/", views.news_api, name="news_api"),
    path("api/superenalotto/", views.superenalotto_api, name="superenalotto_api"),
]
