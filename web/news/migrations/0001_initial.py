from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NewsItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_id", models.CharField(max_length=64, unique=True)),
                ("link", models.URLField(blank=True)),
                ("pub_date_text", models.CharField(blank=True, max_length=128)),
                ("published_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("title_it", models.CharField(max_length=255)),
                ("summary_it", models.TextField(blank=True)),
                ("title_la", models.CharField(blank=True, max_length=255)),
                ("summary_la", models.TextField(blank=True)),
                ("title_en", models.CharField(blank=True, max_length=255)),
                ("summary_en", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-published_at", "-created_at")},
        ),
    ]
