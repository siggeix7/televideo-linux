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
    path("superenalotto/", views.superenalotto_landing, name="superenalotto_landing"),
    path("superenalotto/storico-estrazioni/", views.superenalotto, name="superenalotto"),
    path("superenalotto/storico-montepremi/", views.storico_montepremi, name="storico_montepremi"),
    path("superenalotto/fanta-super/", views.fanta_super, name="fanta_super"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("healthz/", views.healthcheck, name="healthcheck"),
    path("sw.js", views.service_worker_js, name="service_worker"),
    path("api/news/", views.news_api, name="news_api"),
    path("api/meteo/openweather/<str:layer>/<int:z>/<int:x>/<int:y>.png", views.openweather_tile, name="openweather_tile"),
    path("api/superenalotto/", views.superenalotto_api, name="superenalotto_api"),
    path("api/superenalotto/montepremi/", views.montepremi_api, name="montepremi_api"),
    path("api/superenalotto/fanta-super/", views.fanta_super_api, name="fanta_super_api"),
    path("feed.xml", views.atom_feed, name="atom_feed"),
]
