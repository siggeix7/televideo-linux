from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=32, unique=True)),
                ("page", models.PositiveSmallIntegerField(blank=True, db_index=True, null=True)),
                ("name_it", models.CharField(max_length=80)),
                ("name_la", models.CharField(blank=True, max_length=80)),
                ("name_en", models.CharField(blank=True, max_length=80)),
                ("sort_order", models.PositiveSmallIntegerField(db_index=True, default=0)),
                ("active", models.BooleanField(default=True)),
                ("fetched_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ("sort_order", "name_it"), "verbose_name_plural": "categories"},
        ),
        migrations.AddField(
            model_name="newsitem",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="items", to="news.category"),
        ),
        migrations.AddField(
            model_name="newsitem",
            name="source_page",
            field=models.CharField(blank=True, max_length=16),
        ),
    ]
