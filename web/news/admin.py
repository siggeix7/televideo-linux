from django.contrib import admin

from .models import NewsItem


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ("title_it", "pub_date_text", "fetched_at")
    search_fields = ("title_it", "summary_it", "title_la", "title_en")
    readonly_fields = ("source_id", "created_at", "fetched_at")
