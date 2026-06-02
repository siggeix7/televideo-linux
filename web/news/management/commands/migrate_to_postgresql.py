import json
import sys
import tempfile
from collections import defaultdict

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections, connection


def _fix_postgres_sequences():
    cursor = connection.cursor()
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            table = model._meta.db_table
            cursor.execute(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {}".format(table),
                [table],
            )
            cursor.fetchall()
    cursor.close()


def _existing_pks_from_postgres(model):
    """Return set of existing primary keys for a model in the default (PostgreSQL) database."""
    pk_field = model._meta.pk.name
    try:
        return set(model.objects.using("default").values_list(pk_field, flat=True))
    except Exception:
        return set()


class Command(BaseCommand):
    help = "Copies data from SQLite into PostgreSQL (idempotent). Requires POSTGRES_HOST to be configured."

    def handle(self, *args, **options):
        db_configs = connections.databases

        if "sqlite" not in db_configs or db_configs["default"]["ENGINE"] == "django.db.backends.sqlite3":
            self.stderr.write(
                self.style.ERROR(
                    "PostgreSQL not configured. Set POSTGRES_HOST and restart."
                )
            )
            sys.exit(1)

        self.stdout.write(self.style.NOTICE("Step 1/5: migrating PostgreSQL schema ..."))
        call_command("migrate", "--database=default", interactive=False)

        self.stdout.write(self.style.NOTICE("Step 2/5: dumping SQLite data ..."))
        dump_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        call_command(
            "dumpdata",
            "--database=sqlite",
            "--indent=2",
            "--natural-foreign",
            "--natural-primary",
            "--exclude=contenttypes",
            "--exclude=auth.permission",
            "--exclude=sessions",
            stdout=dump_file,
        )
        dump_file.close()

        self.stdout.write(self.style.NOTICE("Step 3/5: filtering out records already in PostgreSQL ..."))
        with open(dump_file.name) as f:
            all_objects = json.load(f)

        # Group objects by model
        by_model = defaultdict(list)
        for obj in all_objects:
            by_model[obj["model"]].append(obj)

        new_objects = []
        skipped_total = 0

        for model_label, objects in by_model.items():
            try:
                model = apps.get_model(model_label)
            except LookupError:
                new_objects.extend(objects)
                continue

            existing = _existing_pks_from_postgres(model)
            added = 0
            for obj in objects:
                if obj["pk"] in existing:
                    skipped_total += 1
                else:
                    new_objects.append(obj)
                    added += 1
            if added or (len(objects) - added) > 0:
                self.stdout.write(
                    f"  {model_label}: {added} new, {len(objects) - added} skipped (already present)"
                )

        if skipped_total:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Skipped {skipped_total} records already present in PostgreSQL."
                )
            )

        if not new_objects:
            self.stdout.write(self.style.SUCCESS("No new records to import. PostgreSQL is up to date."))
            import os
            os.unlink(dump_file.name)
            return

        self.stdout.write(self.style.NOTICE(f"Step 4/5: loading {len(new_objects)} new records into PostgreSQL ..."))
        filtered_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(new_objects, filtered_file, indent=2)
        filtered_file.close()

        try:
            call_command("loaddata", "--database=default", filtered_file.name)
        finally:
            import os
            os.unlink(dump_file.name)
            os.unlink(filtered_file.name)

        self.stdout.write(self.style.NOTICE("Step 5/5: fixing PostgreSQL sequences ..."))
        _fix_postgres_sequences()

        self.stdout.write(self.style.SUCCESS("Migration to PostgreSQL completed."))
