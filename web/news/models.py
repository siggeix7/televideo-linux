from django.db import models


class NewsItem(models.Model):
    source_id = models.CharField(max_length=64, unique=True)
    link = models.URLField(blank=True)
    pub_date_text = models.CharField(max_length=128, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    title_it = models.CharField(max_length=255)
    summary_it = models.TextField(blank=True)
    title_la = models.CharField(max_length=255, blank=True)
    summary_la = models.TextField(blank=True)
    title_en = models.CharField(max_length=255, blank=True)
    summary_en = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")

    def __str__(self) -> str:
        return self.title_it

    def title_for(self, language: str) -> str:
        if language == "la" and self.title_la:
            return self.title_la
        if language == "en" and self.title_en:
            return self.title_en
        return self.title_it

    def summary_for(self, language: str) -> str:
        if language == "la" and self.summary_la:
            return self.summary_la
        if language == "en" and self.summary_en:
            return self.summary_en
        return self.summary_it
