"""Idempotent seed of the South American capitals (L2): python manage.py seed_locations."""

from django.core.management.base import BaseCommand

from locations.services import seed


class Command(BaseCommand):
    help = "Insert the capitals of South America that are missing (never overwrites)."

    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        result = seed()
        self.stdout.write(f"locations: created={result['created']} skipped={result['skipped']}")
