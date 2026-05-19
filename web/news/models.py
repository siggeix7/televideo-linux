from django.db import models


def clean_summary(value: str) -> str:
    prefixes = (
        "Dalle tavole del Televideo: ",
        "From the Televideo chronicle: ",
        "In chronicis scriptum est: ",
    )
    suffixes = (
        " Haec rettulerunt cursores Televidei.",
        " Haec rettulerunt cursores Televidei",
    )
    for prefix in prefixes:
        if value.startswith(prefix):
            value = value[len(prefix):]
    for suffix in suffixes:
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    return value.strip()


class Category(models.Model):
    code = models.SlugField(max_length=32, unique=True)
    page = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    name_it = models.CharField(max_length=80)
    name_la = models.CharField(max_length=80, blank=True)
    name_en = models.CharField(max_length=80, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    active = models.BooleanField(default=True)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("sort_order", "name_it")
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name_it

    def name_for(self, language: str) -> str:
        if language == "la" and self.name_la:
            return self.name_la
        if language == "en" and self.name_en:
            return self.name_en
        return self.name_it


class NewsItem(models.Model):
    source_id = models.CharField(max_length=64, unique=True)
    category = models.ForeignKey(Category, null=True, blank=True, related_name="items", on_delete=models.SET_NULL)
    source_page = models.CharField(max_length=16, blank=True)
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
            return clean_summary(self.summary_la)
        if language == "en" and self.summary_en:
            return clean_summary(self.summary_en)
        return clean_summary(self.summary_it)


class SuperEnalottoDraw(models.Model):
    draw_number = models.PositiveIntegerField()
    draw_date = models.DateField(db_index=True)
    winning_numbers = models.JSONField(default=list)
    jolly_number = models.PositiveSmallIntegerField(null=True, blank=True)
    superstar_number = models.PositiveSmallIntegerField(null=True, blank=True)
    jackpot = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    prize_pool = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    raw_text = models.TextField(blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-draw_date", "-draw_number")
        constraints = [models.UniqueConstraint(fields=("draw_number", "draw_date"), name="unique_superenalotto_draw")]

    def __str__(self) -> str:
        return f"Concorso {self.draw_number} del {self.draw_date.isoformat()}"
