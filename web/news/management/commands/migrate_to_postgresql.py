import sys
import tempfile

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "Copies data from SQLite into PostgreSQL. Requires POSTGRES_HOST to be configured."

    def handle(self, *args, **options):
        db_configs = connections.databases

        if "sqlite" not in db_configs or db_configs["default"]["ENGINE"] == "django.db.backends.sqlite3":
            self.stderr.write(
                self.style.ERROR(
                    "PostgreSQL not configured. Set POSTGRES_HOST and restart."
                )
            )
            sys.exit(1)

        self.stdout.write(self.style.NOTICE("Step 1/3: dumping SQLite data ..."))
        dump_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        call_command(
            "dumpdata",
            "--database=sqlite",
            "--natural-foreign",
            "--natural-primary",
            "--exclude=contenttypes",
            "--exclude=auth.permission",
            "--exclude=sessions",
            stdout=dump_file,
        )
        dump_file.close()

        self.stdout.write(self.style.NOTICE("Step 2/3: migrating PostgreSQL ..."))
        call_command("migrate", "--database=default", interactive=False)

        self.stdout.write(self.style.NOTICE("Step 3/3: loading data into PostgreSQL ..."))
        try:
            call_command("loaddata", "--database=default", dump_file.name)
        finally:
            import os
            os.unlink(dump_file.name)

        self.stdout.write(self.style.SUCCESS("Migration to PostgreSQL completed."))
