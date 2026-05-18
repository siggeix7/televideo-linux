from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("news", "0002_categories"),
    ]

    operations = [
        migrations.CreateModel(
            name="SuperEnalottoDraw",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("draw_number", models.PositiveIntegerField()),
                ("draw_date", models.DateField(db_index=True)),
                ("winning_numbers", models.JSONField(default=list)),
                ("jolly_number", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("superstar_number", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("jackpot", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("prize_pool", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("raw_text", models.TextField(blank=True)),
                ("fetched_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-draw_date", "-draw_number")},
        ),
        migrations.AddConstraint(
            model_name="superenalottodraw",
            constraint=models.UniqueConstraint(fields=("draw_number", "draw_date"), name="unique_superenalotto_draw"),
        ),
    ]
