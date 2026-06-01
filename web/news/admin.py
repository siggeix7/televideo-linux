from django.contrib import admin

from .models import Category, NewsItem, OpenWeatherCity, SuperEnalottoDraw


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_it", "page", "sort_order", "active", "fetched_at")
    list_filter = ("active",)
    search_fields = ("name_it", "name_la", "name_en", "code")


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ("title_it", "category", "source_page", "pub_date_text", "fetched_at")
    list_filter = ("category",)
    search_fields = ("title_it", "summary_it", "title_la", "title_en")
    readonly_fields = ("source_id", "created_at", "fetched_at")


@admin.register(SuperEnalottoDraw)
class SuperEnalottoDrawAdmin(admin.ModelAdmin):
    list_display = ("draw_number", "draw_date", "jackpot", "prize_pool", "fetched_at")
    search_fields = ("draw_number", "raw_text")
    readonly_fields = ("fetched_at",)


@admin.register(OpenWeatherCity)
class OpenWeatherCityAdmin(admin.ModelAdmin):
    list_display = ("city", "region_slug", "condition", "temp", "sunrise_at", "sunset_at", "fetched_at", "last_attempt_at")
    list_filter = ("region_slug",)
    search_fields = ("city", "query", "condition")
    readonly_fields = ("created_at", "updated_at", "fetched_at", "last_attempt_at")
