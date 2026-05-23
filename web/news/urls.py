from django.urls import path

from . import views


app_name = "news"

urlpatterns = [
    path("", views.home, name="home"),
    path("tv/", views.tv, name="tv"),
    path("cultura/", views.culture, name="culture"),
    path("ambiente/", views.environment, name="environment"),
    path("lavoro/", views.work, name="work"),
    path("sport/", views.sport, name="sport"),
    path("meteo/", views.weather, name="weather"),
    path("viaggi/", views.travel, name="travel"),
    path("giochi/", views.games, name="games"),
    path("regioni/", views.regions, name="regions"),
    path("regioni/<slug:region_slug_value>/", views.regions, name="region"),
    path("superenalotto/", views.superenalotto, name="superenalotto"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("healthz/", views.healthcheck, name="healthcheck"),
    path("sw.js", views.service_worker_js, name="service_worker"),
    path("api/news/", views.news_api, name="news_api"),
    path("api/superenalotto/", views.superenalotto_api, name="superenalotto_api"),
    path("feed.xml", views.atom_feed, name="atom_feed"),
]
