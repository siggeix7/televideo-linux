from __future__ import annotations

import csv
import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from news.models import SuperEnalottoDraw


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import SuperEnalotto draws from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the CSV file")
        parser.add_argument("--skip-existing", action="store_true", dest="skip_existing", default=True, help="Skip draws that are already in the DB (default)")
        parser.add_argument("--overwrite", action="store_false", dest="skip_existing", help="Overwrite existing draws with CSV data")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        skip_existing = options["skip_existing"]

        imported = 0
        skipped = 0
        errors = 0
        updated = 0

        with open(csv_path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    draw_date = date.fromisoformat(row["data"].strip())
                    draw_number = int(row["concorso"].strip())
                    winning_numbers = [
                        int(row["n1"].strip()),
                        int(row["n2"].strip()),
                        int(row["n3"].strip()),
                        int(row["n4"].strip()),
                        int(row["n5"].strip()),
                        int(row["n6"].strip()),
                    ]
                    jolly_str = row.get("jolly", "").strip()
                    superstar_str = row.get("superstar", "").strip()
                    jolly_number = int(jolly_str) if jolly_str else None
                    superstar_number = int(superstar_str) if superstar_str else None

                    existing = SuperEnalottoDraw.objects.filter(
                        draw_number=draw_number, draw_date=draw_date
                    ).first()

                    if existing:
                        if skip_existing:
                            skipped += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"skipped (exists): {row['data']} concorso {draw_number}")
                            )
                        else:
                            existing.winning_numbers = winning_numbers
                            existing.jolly_number = jolly_number
                            existing.superstar_number = superstar_number
                            if not existing.raw_text:
                                existing.raw_text = (
                                    f"Fonte archivio storico: "
                                    f"Concorso N.{draw_number} del {draw_date.isoformat()} "
                                    f"numeri {' '.join(str(n) for n in winning_numbers)} "
                                    f"Jolly {jolly_number or '—'} SuperStar {superstar_number or '—'}"
                                )
                            existing.save()
                            updated += 1
                            self.stdout.write(
                                self.style.WARNING(f"updated: {row['data']} concorso {draw_number}")
                            )
                    else:
                        defaults = {
                            "winning_numbers": winning_numbers,
                            "jolly_number": jolly_number,
                            "superstar_number": superstar_number,
                            "raw_text": (
                                f"Fonte archivio storico: "
                                f"Concorso N.{draw_number} del {draw_date.isoformat()} "
                                f"numeri {' '.join(str(n) for n in winning_numbers)} "
                                f"Jolly {jolly_number or '—'} SuperStar {superstar_number or '—'}"
                            ),
                        }
                        SuperEnalottoDraw.objects.create(
                            draw_number=draw_number,
                            draw_date=draw_date,
                            **defaults,
                        )
                        imported += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"imported: {row['data']} concorso {draw_number}")
                        )
                except Exception as exc:
                    errors += 1
                    self.stderr.write(
                        self.style.ERROR(f"error on row {row.get('data', '?')}: {exc}")
                    )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Imported: {imported}, Skipped: {skipped}, Updated: {updated}, Errors: {errors}"
            )
        )
